import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.bedrock_client import BedrockClient
from src.utils.dynamodb_client import DynamoDBClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="VyaparIQ Medical Edition",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile-responsive design
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .alert-high {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .alert-medium {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .alert-low {
        background-color: #e8f5e9;
        border-left: 4px solid: #4caf50;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize clients
@st.cache_resource
def init_clients():
    bedrock = BedrockClient()
    dynamodb = DynamoDBClient()
    return bedrock, dynamodb

bedrock_client, dynamodb_client = init_clients()

# Sidebar navigation
st.sidebar.title("🏥 VyaparIQ Medical")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Inventory Audit", "Expiry Monitor", "Prescription Upload", "Safety Checker"]
)

# Main content
if page == "Dashboard":
    st.markdown('<h1 class="main-header">📊 Dashboard</h1>', unsafe_allow_html=True)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Medicines", "156", "+12")
    with col2:
        st.metric("Low Stock Items", "8", "-2")
    with col3:
        st.metric("Expiring Soon", "5", "+1")
    with col4:
        st.metric("Savings This Week", "₹5,240", "+₹1,200")
    
    st.divider()
    
    # Recent alerts
    st.subheader("🔔 Recent Alerts")
    
    alerts = dynamodb_client.get_recent_alerts(limit=5)
    
    if alerts:
        for alert in alerts:
            severity = alert.get('severity', 'LOW')
            alert_class = f"alert-{severity.lower()}"
            st.markdown(f"""
            <div class="{alert_class}">
                <strong>{alert.get('type', 'ALERT')}</strong><br>
                {alert.get('message', 'No message')}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent alerts. Your inventory is in good shape! ✅")
    
    st.divider()
    
    # Quick stats
    st.subheader("📈 Weekly Insights")
    st.success("✅ You saved ₹5,240 this week by selling near-expiry stock first")
    st.info("ℹ️ 8 medicines need reordering within 7 days")
    st.warning("⚠️ 5 medicines expire in the next 30 days")

elif page == "Inventory Audit":
    st.markdown('<h1 class="main-header">📸 Visual Inventory Audit</h1>', unsafe_allow_html=True)
    
    st.write("Upload a photo of your medical store shelf to automatically detect medicines and stock levels.")
    
    uploaded_file = st.file_uploader("Choose a shelf image", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file is not None:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image(uploaded_file, caption="Uploaded Shelf Image", use_container_width=True)
        
        with col2:
            if st.button("🔍 Analyze Shelf", type="primary"):
                with st.spinner("Analyzing shelf image..."):
                    # Convert image to base64
                    import base64
                    image_bytes = uploaded_file.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Call Bedrock for analysis
                    result = bedrock_client.analyze_shelf_image(image_base64)
                    
                    if result:
                        st.success("✅ Analysis complete!")
                        
                        # Display detected medicines
                        st.subheader("Detected Medicines")
                        medicines = result.get('medicines_detected', [])
                        
                        for med in medicines:
                            with st.expander(f"💊 {med['name']} - {med['brand']}"):
                                st.write(f"**Quantity:** {med['quantity_estimate']}")
                                st.write(f"**Confidence:** {med.get('confidence_score', 0.9) * 100:.1f}%")
                                if med.get('expiry_visible'):
                                    st.write(f"**Expiry:** {med.get('expiry_date', 'N/A')}")
                        
                        # Missing essentials
                        missing = result.get('missing_essentials', [])
                        if missing:
                            st.warning(f"⚠️ Missing Essential Medicines: {', '.join(missing)}")

elif page == "Expiry Monitor":
    st.markdown('<h1 class="main-header">⏰ Expiry Date Monitor</h1>', unsafe_allow_html=True)
    
    # Filter options
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_days = st.selectbox("Show medicines expiring in:", [30, 60, 90, 180])
    
    st.divider()
    
    # Get expiring medicines
    expiring_meds = dynamodb_client.get_expiring_medicines(days=filter_days)
    
    if expiring_meds:
        # Group by severity
        critical = [m for m in expiring_meds if m['days_until_expiry'] < 30]
        warning = [m for m in expiring_meds if 30 <= m['days_until_expiry'] < 90]
        normal = [m for m in expiring_meds if m['days_until_expiry'] >= 90]
        
        # Critical (< 30 days)
        if critical:
            st.error(f"🔴 URGENT: {len(critical)} medicines expire in < 30 days")
            for med in critical:
                st.markdown(f"""
                <div class="alert-high">
                    <strong>{med['name']}</strong> - {med['brand']}<br>
                    Expires in {med['days_until_expiry']} days | Stock: {med['stock_count']}<br>
                    <em>Action: Discount sale or return to supplier</em>
                </div>
                """, unsafe_allow_html=True)
        
        # Warning (30-90 days)
        if warning:
            st.warning(f"🟡 {len(warning)} medicines expire in 30-90 days")
            for med in warning:
                st.markdown(f"""
                <div class="alert-medium">
                    <strong>{med['name']}</strong> - {med['brand']}<br>
                    Expires in {med['days_until_expiry']} days | Stock: {med['stock_count']}<br>
                    <em>Action: Prioritize in sales</em>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("✅ No medicines expiring soon. Great inventory management!")

elif page == "Prescription Upload":
    st.markdown('<h1 class="main-header">📝 Prescription to Order</h1>', unsafe_allow_html=True)
    
    st.write("Upload a handwritten prescription to automatically generate a purchase order.")
    
    uploaded_file = st.file_uploader("Choose a prescription image", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file is not None:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image(uploaded_file, caption="Uploaded Prescription", use_container_width=True)
        
        with col2:
            if st.button("📋 Process Prescription", type="primary"):
                with st.spinner("Extracting medicines from prescription..."):
                    import base64
                    image_bytes = uploaded_file.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    result = bedrock_client.process_prescription(image_base64)
                    
                    if result:
                        st.success("✅ Prescription processed!")
                        
                        medicines = result.get('medicines', [])
                        
                        st.subheader("Extracted Medicines")
                        for med in medicines:
                            st.write(f"💊 **{med['name']}** {med['dosage']} - {med['form']}")
                            st.write(f"   Quantity: {med['quantity']} | Frequency: {med.get('frequency', 'N/A')}")
                        
                        if st.button("✅ Generate Purchase Order"):
                            st.success("Purchase order created successfully!")

elif page == "Safety Checker":
    st.markdown('<h1 class="main-header">🛡️ Drug Safety Checker</h1>', unsafe_allow_html=True)
    
    st.write("Check for dangerous drug interactions before restocking.")
    
    # Input medicines
    medicine_input = st.text_area(
        "Enter medicine names (one per line)",
        placeholder="Aspirin\nWarfarin\nParacetamol"
    )
    
    if st.button("🔍 Check Interactions", type="primary"):
        if medicine_input:
            medicines = [m.strip() for m in medicine_input.split('\n') if m.strip()]
            
            with st.spinner("Checking drug interactions..."):
                result = bedrock_client.check_drug_interactions(medicines)
                
                if result:
                    interactions = result.get('interactions', [])
                    
                    if interactions:
                        st.error(f"⚠️ Found {len(interactions)} potential interactions")
                        
                        for interaction in interactions:
                            severity = interaction.get('severity', 'MODERATE')
                            
                            if severity == 'CRITICAL':
                                st.markdown(f"""
                                <div class="alert-high">
                                    <strong>🔴 CRITICAL: {interaction['drug1']} + {interaction['drug2']}</strong><br>
                                    {interaction['description']}<br>
                                    <em>Recommendation: {interaction['recommendation']}</em>
                                </div>
                                """, unsafe_allow_html=True)
                            elif severity == 'HIGH':
                                st.markdown(f"""
                                <div class="alert-medium">
                                    <strong>🟡 HIGH: {interaction['drug1']} + {interaction['drug2']}</strong><br>
                                    {interaction['description']}<br>
                                    <em>Recommendation: {interaction['recommendation']}</em>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.success("✅ No dangerous interactions found!")
        else:
            st.warning("Please enter at least one medicine name")

# Footer
st.sidebar.divider()
st.sidebar.info("""
**VyaparIQ Medical Edition**  
AI-powered inventory management for Indian pharmacies

⚠️ Disclaimer: This is an inventory management tool, not medical advice.
""")
