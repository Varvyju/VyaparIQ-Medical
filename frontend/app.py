import streamlit as st
import boto3
import json
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image
import io
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="VyaparIQ Medical",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1E88E5;
    }
    .alert-high {
        background-color: #ffebee;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #f44336;
    }
    .alert-medium {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff9800;
    }
    .alert-low {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize AWS clients
@st.cache_resource
def get_aws_clients():
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    return {
        's3': session.client('s3'),
        'dynamodb': session.resource('dynamodb'),
        'lambda': session.client('lambda')
    }

clients = get_aws_clients()
s3 = clients['s3']
dynamodb = clients['dynamodb']
lambda_client = clients['lambda']

# Configuration
S3_BUCKET = os.getenv('S3_BUCKET', 'vyapariq-medical-images')
INVENTORY_TABLE = 'VyaparIQ-Inventory'
ALERTS_TABLE = 'VyaparIQ-Alerts'
PURCHASE_ORDERS_TABLE = 'VyaparIQ-PurchaseOrders'

# Header
st.markdown('<div class="main-header">💊 VyaparIQ Medical</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Powered Inventory & Safety Management for Medical Stores</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/1E88E5/FFFFFF?text=VyaparIQ", use_column_width=True)
    st.markdown("---")
    
    page = st.radio("Navigation", [
        "📊 Dashboard",
        "📸 Shelf Analysis",
        "📋 Prescription Processing",
        "⚠️ Alerts",
        "📦 Inventory",
        "🛒 Purchase Orders"
    ])
    
    st.markdown("---")
    st.markdown("### Quick Stats")
    
    # Get quick stats from DynamoDB
    try:
        inventory_table = dynamodb.Table(INVENTORY_TABLE)
        alerts_table = dynamodb.Table(ALERTS_TABLE)
        
        inventory_response = inventory_table.scan(Select='COUNT')
        total_medicines = inventory_response.get('Count', 0)
        
        alerts_response = alerts_table.scan(
            FilterExpression='resolved = :val',
            ExpressionAttributeValues={':val': False},
            Select='COUNT'
        )
        active_alerts = alerts_response.get('Count', 0)
        
        st.metric("Total Medicines", total_medicines)
        st.metric("Active Alerts", active_alerts)
    except Exception as e:
        st.warning("Unable to load stats")

# Page routing
if page == "📊 Dashboard":
    st.header("Dashboard Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        # Fetch inventory data
        inventory_table = dynamodb.Table(INVENTORY_TABLE)
        inventory_response = inventory_table.scan()
        medicines = inventory_response.get('Items', [])
        
        # Fetch alerts
        alerts_table = dynamodb.Table(ALERTS_TABLE)
        alerts_response = alerts_table.scan()
        alerts = alerts_response.get('Items', [])
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Medicines", len(medicines))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            low_stock = sum(1 for m in medicines if int(m.get('stock_quantity', 0)) < 10)
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Low Stock Items", low_stock)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            expiry_alerts = [a for a in alerts if a.get('type') == 'expiry_warning' and not a.get('resolved', False)]
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Expiry Warnings", len(expiry_alerts))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            active_alerts = [a for a in alerts if not a.get('resolved', False)]
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Active Alerts", len(active_alerts))
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Recent alerts section
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("🚨 Recent Alerts")
            if alerts:
                sorted_alerts = sorted(alerts, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
                for alert in sorted_alerts:
                    severity = alert.get('severity', 'low')
                    alert_class = f"alert-{severity}"
                    st.markdown(f'<div class="{alert_class}">', unsafe_allow_html=True)
                    st.markdown(f"**{alert.get('type', 'Unknown').replace('_', ' ').title()}**")
                    st.markdown(alert.get('message', 'No message'))
                    st.markdown(f"*{alert.get('created_at', 'Unknown time')[:10]}*")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No alerts at the moment 🎉")
        
        with col_right:
            st.subheader("📈 Stock Distribution")
            if medicines:
                # Create stock level distribution
                stock_levels = {
                    'Critical (<5)': sum(1 for m in medicines if int(m.get('stock_quantity', 0)) < 5),
                    'Low (5-10)': sum(1 for m in medicines if 5 <= int(m.get('stock_quantity', 0)) < 10),
                    'Medium (10-20)': sum(1 for m in medicines if 10 <= int(m.get('stock_quantity', 0)) < 20),
                    'Good (20+)': sum(1 for m in medicines if int(m.get('stock_quantity', 0)) >= 20)
                }
                
                df_stock = pd.DataFrame(list(stock_levels.items()), columns=['Level', 'Count'])
                st.bar_chart(df_stock.set_index('Level'))
            else:
                st.info("No inventory data yet. Start by analyzing a shelf!")
        
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")

elif page == "📸 Shelf Analysis":
    st.header("Shelf Image Analysis")
    st.markdown("Upload a photo of your medical store shelf to automatically identify medicines and stock levels.")
    
    uploaded_file = st.file_uploader("📷 Upload Shelf Image", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Uploaded Image")
            image = Image.open(uploaded_file)
            st.image(image, use_column_width=True)
        
        with col2:
            st.subheader("Analysis")
            
            if st.button("🔍 Analyze Shelf", type="primary"):
                with st.spinner("Analyzing image with AI..."):
                    try:
                        # Upload to S3
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        s3_key = f"shelf_images/{timestamp}_{uploaded_file.name}"
                        
                        # Convert image to bytes
                        img_byte_arr = io.BytesIO()
                        
                        # --- FIX: Convert RGBA to RGB ---
                        if image.mode in ('RGBA', 'P'):
                            image = image.convert('RGB')
                        # -------------------------------
                        
                        image.save(img_byte_arr, format='JPEG')
                        img_byte_arr.seek(0)
                        
                        s3.upload_fileobj(img_byte_arr, S3_BUCKET, s3_key)
                        
                        # Invoke Lambda function
                        response = lambda_client.invoke(
                            FunctionName='analyze-shelf-image',
                            InvocationType='RequestResponse',
                            Payload=json.dumps({
                                'bucket': S3_BUCKET,
                                'key': s3_key
                            })
                        )
                        
                        result = json.loads(response['Payload'].read())
                        
                        if result['statusCode'] == 200:
                            body = json.loads(result['body'])
                            analysis = body['analysis']
                            
                            st.success("✅ Analysis Complete!")
                            
                            # Display results
                            st.markdown("### Medicines Detected")
                            medicines_detected = analysis.get('medicines_detected', [])
                            
                            if medicines_detected:
                                df = pd.DataFrame(medicines_detected)
                                st.dataframe(df[['name', 'brand', 'quantity_estimate', 'confidence']], use_container_width=True)
                                
                                st.metric("Total Medicines Found", len(medicines_detected))
                            else:
                                st.warning("No medicines detected in this image")
                            
                            # Missing essentials
                            missing = analysis.get('missing_essentials', [])
                            if missing:
                                st.markdown("### ⚠️ Missing Essential Medicines")
                                for item in missing:
                                    st.warning(f"• {item}")
                            
                            # Recommendations
                            recommendations = analysis.get('recommendations', [])
                            if recommendations:
                                st.markdown("### 💡 Recommendations")
                                for rec in recommendations:
                                    st.info(f"• {rec}")
                        else:
                            st.error("Analysis failed. Please try again.")
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

elif page == "📋 Prescription Processing":
    st.header("Prescription Processing")
    st.markdown("Upload a doctor's prescription to automatically extract medicines and create purchase orders.")
    
    uploaded_file = st.file_uploader("📄 Upload Prescription Image", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Prescription Image")
            image = Image.open(uploaded_file)
            st.image(image, use_column_width=True)
        
        with col2:
            st.subheader("Extracted Information")
            
            if st.button("📝 Process Prescription", type="primary"):
                with st.spinner("Extracting prescription data with AI..."):
                    try:
                        # Upload to S3
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        s3_key = f"prescriptions/{timestamp}_{uploaded_file.name}"
                        
                        img_byte_arr = io.BytesIO()
                        
                        # --- FIX: Convert RGBA to RGB ---
                        if image.mode in ('RGBA', 'P'):
                            image = image.convert('RGB')
                        # -------------------------------
                        
                        image.save(img_byte_arr, format='JPEG')
                        img_byte_arr.seek(0)
                        
                        s3.upload_fileobj(img_byte_arr, S3_BUCKET, s3_key)
                        
                        # Invoke Lambda
                        response = lambda_client.invoke(
                            FunctionName='process-prescription',
                            InvocationType='RequestResponse',
                            Payload=json.dumps({
                                'bucket': S3_BUCKET,
                                'key': s3_key
                            })
                        )
                        
                        result = json.loads(response['Payload'].read())
                        
                        if result['statusCode'] == 200:
                            body = json.loads(result['body'])
                            
                            st.success("✅ Prescription Processed!")
                            
                            # Medicine list
                            prescription = body['prescription']
                            medicines = prescription.get('medicines', [])
                            
                            st.markdown("### 💊 Medicines Prescribed")
                            if medicines:
                                df = pd.DataFrame(medicines)
                                st.dataframe(df[['medicine_name', 'dosage', 'frequency', 'quantity_needed']], use_container_width=True)
                            
                            # Drug interactions
                            interactions = body.get('interactions', [])
                            if interactions:
                                st.markdown("### ⚠️ Drug Interaction Warnings")
                                for interaction in interactions:
                                    severity = interaction['severity']
                                    st.markdown(f'<div class="alert-{severity}">', unsafe_allow_html=True)
                                    st.markdown(f"**{interaction['drug1'].title()} + {interaction['drug2'].title()}**")
                                    st.markdown(f"Risk: {interaction['risk']}")
                                    st.markdown(f"Recommendation: {interaction['recommendation']}")
                                    st.markdown('</div>', unsafe_allow_html=True)
                            else:
                                st.success("✅ No drug interactions detected")
                            
                            # Purchase order
                            purchase_order = body.get('purchase_order', {})
                            if purchase_order:
                                st.markdown("### 🛒 Purchase Order Generated")
                                st.json(purchase_order)
                        else:
                            # Enhanced Error Reporting
                            st.error(f"Processing failed with status: {result.get('statusCode')}")
                            if 'body' in result:
                                st.error(f"Details: {result['body']}")
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

elif page == "⚠️ Alerts":
    st.header("Alerts & Notifications")
    
    try:
        alerts_table = dynamodb.Table(ALERTS_TABLE)
        response = alerts_table.scan()
        alerts = response.get('Items', [])
        
        # Filter options
        filter_type = st.selectbox("Filter by type", ["All", "expiry_warning", "missing_essential", "drug_interaction", "low_stock_warning"])
        show_resolved = st.checkbox("Show resolved alerts")
        
        filtered_alerts = alerts
        if filter_type != "All":
            filtered_alerts = [a for a in filtered_alerts if a.get('type') == filter_type]
        if not show_resolved:
            filtered_alerts = [a for a in filtered_alerts if not a.get('resolved', False)]
        
        # Sort by date
        sorted_alerts = sorted(filtered_alerts, key=lambda x: x.get('created_at', ''), reverse=True)
        
        st.markdown(f"### Showing {len(sorted_alerts)} alerts")
        
        for alert in sorted_alerts:
            severity = alert.get('severity', 'low')
            alert_class = f"alert-{severity}"
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f'<div class="{alert_class}">', unsafe_allow_html=True)
                st.markdown(f"**{alert.get('type', 'Unknown').replace('_', ' ').title()}** - {severity.upper()}")
                st.markdown(alert.get('message', 'No message'))
                if alert.get('recommendation'):
                    st.markdown(f"*Recommendation: {alert.get('recommendation')}*")
                st.markdown(f"*Created: {alert.get('created_at', 'Unknown')[:19]}*")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                if not alert.get('resolved', False):
                    if st.button(f"✓ Resolve", key=alert.get('alert_id')):
                        alerts_table.update_item(
                            Key={'alert_id': alert.get('alert_id')},
                            UpdateExpression='SET resolved = :val',
                            ExpressionAttributeValues={':val': True}
                        )
                        st.rerun()
    
    except Exception as e:
        st.error(f"Error loading alerts: {str(e)}")

elif page == "📦 Inventory":
    st.header("Medicine Inventory")
    
    try:
        inventory_table = dynamodb.Table(INVENTORY_TABLE)
        response = inventory_table.scan()
        medicines = response.get('Items', [])
        
        if medicines:
            # Convert to DataFrame
            df = pd.DataFrame(medicines)
            
            # Sort by stock quantity
            df = df.sort_values('stock_quantity', ascending=True)
            
            # Display
            st.dataframe(df[['medicine_name', 'brand', 'stock_quantity', 'expiry_date', 'last_scanned']], use_container_width=True)
            
            # Export option
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"inventory_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No inventory data yet. Start by analyzing a shelf image!")
    
    except Exception as e:
        st.error(f"Error loading inventory: {str(e)}")

elif page == "🛒 Purchase Orders":
    st.header("Purchase Orders")
    
    try:
        po_table = dynamodb.Table(PURCHASE_ORDERS_TABLE)
        response = po_table.scan()
        orders = response.get('Items', [])
        
        if orders:
            sorted_orders = sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True)
            
            for order in sorted_orders:
                with st.expander(f"Order {order.get('order_id')} - {order.get('status', 'pending').upper()}"):
                    st.markdown(f"**Created:** {order.get('created_at', 'Unknown')[:19]}")
                    st.markdown(f"**Total Items:** {order.get('total_items', 0)}")
                    
                    if order.get('patient_name'):
                        st.markdown(f"**Patient:** {order.get('patient_name')}")
                    if order.get('doctor_name'):
                        st.markdown(f"**Doctor:** {order.get('doctor_name')}")
                    
                    # Items
                    items = order.get('items', [])
                    if items:
                        st.markdown("**Items:**")
                        df_items = pd.DataFrame(items)
                        st.dataframe(df_items, use_container_width=True)
                    
                    # Interactions warning
                    if order.get('has_interactions'):
                        st.warning("⚠️ This order has drug interaction warnings. Check alerts.")
        else:
            st.info("No purchase orders yet. Process a prescription to create one!")
    
    except Exception as e:
        st.error(f"Error loading purchase orders: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>VyaparIQ Medical • Powered by AWS Bedrock & Claude AI • Built for AI for Bharat Hackathon 2026</p>
</div>
""", unsafe_allow_html=True)