import json
import boto3
import base64
import os
from datetime import datetime, timedelta

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Environment variables
INVENTORY_TABLE = os.environ.get('INVENTORY_TABLE', 'VyaparIQ-Inventory')
ALERTS_TABLE = os.environ.get('ALERTS_TABLE', 'VyaparIQ-Alerts')

# Configuration
MIN_CONFIDENCE_THRESHOLD = 0.75  # Only save high-confidence detections

def analyze_image_with_bedrock(image_base64):
    """
    Call Bedrock Nova Pro to analyze medical shelf image
    """
    system_prompt = """You are an expert pharmacist analyzing a medical store shelf in India.

    Analyze this image and return ONLY valid JSON (no markdown, no explanation):

    {
      "medicines_detected": [
        {
          "name": "Generic name of medicine",
          "brand": "Brand name if visible",
          "quantity_estimate": 10,
          "expiry_visible": true,
          "expiry_date": "2025-12-31",
          "confidence": 0.95,
          "location_on_shelf": "top/middle/bottom"
        }
      ],
      "missing_essentials": ["List of common essential medicines NOT visible"],
      "shelf_condition": "organized",
      "overall_stock_level": "medium",
      "recommendations": ["Specific actionable recommendations"],
      "confidence_score": 0.95
    }

    Important guidelines:
    - Focus on Indian medicine brands (Dolo, Crocin, Combiflam, Azithral, etc.)
    - Be conservative with quantity estimates
    - Mark confidence low if labels are unclear
    - Common essentials to check: Paracetamol, ORS, Bandages, Antiseptic, Insulin
    - If expiry date is visible but unclear, mark expiry_visible as false
    - Estimate quantity by counting visible boxes/strips
    - Be very conservative with confidence scores - only use 0.9+ if you're certain"""

    request_body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    { "text": system_prompt },
                    { 
                        "image": { 
                            "format": "jpeg", 
                            "source": { "bytes": image_base64 } 
                        } 
                    }
                ]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 4000,
            "temperature": 0.1
        }
    }
    
    response = bedrock_runtime.invoke_model(
        modelId='amazon.nova-pro-v1:0',
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    ai_response = response_body['output']['message']['content'][0]['text']
    
    # Clean up markdown if present
    ai_response = ai_response.strip()
    if '```json' in ai_response:
        ai_response = ai_response.split('```json')[1].split('```')[0].strip()
    elif '```' in ai_response:
        ai_response = ai_response.split('```')[1].split('```')[0].strip()
    
    return json.loads(ai_response)


def estimate_medicine_price(medicine_name, quantity):
    """
    Estimate price based on medicine category
    Smart pricing for better revenue calculations
    """
    name_lower = medicine_name.lower()
    
    # Antibiotics (higher priced)
    if any(x in name_lower for x in ['azithral', 'augmentin', 'amoxicillin', 'ciprofloxacin', 'azithromycin']):
        return 120
    
    # Chronic disease medications (moderate-high price)
    elif any(x in name_lower for x in ['insulin', 'metformin', 'glycomet', 'aspirin', 'ecosprin']):
        return 95
    
    # Common OTC medicines (lower price)
    elif any(x in name_lower for x in ['paracetamol', 'dolo', 'crocin', 'cetzine', 'cetirizine']):
        return 45
    
    # Vitamins/supplements (moderate price)
    elif any(x in name_lower for x in ['vitamin', 'calcium', 'shelcal', 'becosules', 'iron']):
        return 65
    
    # Pain relief
    elif any(x in name_lower for x in ['combiflam', 'brufen', 'ibuprofen', 'voveran', 'diclofenac']):
        return 55
    
    # Default average price
    else:
        return 85


def save_to_dynamodb(analysis_result, image_key):
    """
    Save analysis results to DynamoDB with REVENUE RISK CALCULATION
    Enhanced with deduplication, stock alerts, and data validation
    """
    inventory_table = dynamodb.Table(INVENTORY_TABLE)
    alerts_table = dynamodb.Table(ALERTS_TABLE)
    
    timestamp = datetime.utcnow().isoformat()
    
    medicines = analysis_result.get('medicines_detected', [])
    saved_count = 0
    skipped_count = 0
    
    for medicine in medicines:
        # CONFIDENCE FILTERING - Skip low-confidence detections
        confidence = medicine.get('confidence', 0.0)
        
        if confidence < MIN_CONFIDENCE_THRESHOLD:
            print(f"⚠️ Skipping {medicine.get('name')} - confidence too low: {confidence:.2f}")
            skipped_count += 1
            continue
        
        safe_name = medicine.get('name', 'Unknown').lower().replace(' ', '_')
        safe_brand = medicine.get('brand', 'generic').lower().replace(' ', '_')
        
        # DEDUPLICATION - Use medicine+brand as unique ID (no timestamp)
        medicine_id = f"{safe_name}_{safe_brand}"
        
        # SMART PRICING
        quantity = medicine.get('quantity_estimate', 0)
        estimated_price = estimate_medicine_price(medicine.get('name', ''), quantity)
        estimated_value = quantity * estimated_price
        
        try:
            # Check if medicine already exists
            existing_response = inventory_table.get_item(Key={'medicine_id': medicine_id})
            
            if 'Item' in existing_response:
                # UPDATE EXISTING MEDICINE
                existing = existing_response['Item']
                old_qty = existing.get('stock_quantity', 0)
                
                inventory_table.update_item(
                    Key={'medicine_id': medicine_id},
                    UpdateExpression='SET stock_quantity = :qty, last_scanned = :ts, confidence = :conf, image_reference = :img, estimated_value = :val',
                    ExpressionAttributeValues={
                        ':qty': quantity,
                        ':ts': timestamp,
                        ':conf': str(confidence),
                        ':img': image_key,
                        ':val': estimated_value
                    }
                )
                print(f"✅ Updated: {medicine.get('name')} (qty: {old_qty} → {quantity})")
                
                # STOCK CHANGE ALERTS
                if quantity > old_qty + 10:
                    # Significant restock
                    alert = {
                        'alert_id': f"restock_{medicine_id}_{timestamp}",
                        'type': 'stock_increase',
                        'severity': 'low',
                        'medicine_name': medicine['name'],
                        'old_quantity': old_qty,
                        'new_quantity': quantity,
                        'created_at': timestamp,
                        'resolved': False,
                        'message': f"📦 {medicine['name']} restocked: {old_qty} → {quantity} units"
                    }
                    alerts_table.put_item(Item=alert)
                
                elif quantity < old_qty - 10 and quantity < 5:
                    # Stock dropped significantly AND now low
                    alert = {
                        'alert_id': f"stock_drop_{medicine_id}_{timestamp}",
                        'type': 'low_stock_warning',
                        'severity': 'medium',
                        'medicine_name': medicine['name'],
                        'old_quantity': old_qty,
                        'new_quantity': quantity,
                        'created_at': timestamp,
                        'resolved': False,
                        'message': f"⚠️ {medicine['name']} stock dropped: {old_qty} → {quantity} units. Consider restocking."
                    }
                    alerts_table.put_item(Item=alert)
            
            else:
                # CREATE NEW MEDICINE
                inventory_item = {
                    'medicine_id': medicine_id,
                    'medicine_name': medicine.get('name', 'Unknown'),
                    'brand': medicine.get('brand', 'Unknown'),
                    'stock_quantity': quantity,
                    'expiry_date': medicine.get('expiry_date'),
                    'confidence': str(confidence),
                    'location': medicine.get('location_on_shelf', 'unknown'),
                    'last_scanned': timestamp,
                    'first_detected': timestamp,
                    'image_reference': image_key,
                    'estimated_value': estimated_value
                }
                inventory_table.put_item(Item=inventory_item)
                print(f"✅ Created: {medicine.get('name')} (qty: {quantity}, conf: {confidence:.2f})")
            
            saved_count += 1
        
        except Exception as e:
            print(f"❌ Error saving {medicine.get('name')}: {e}")
            continue
        
        # EXPIRY DATE ALERTS with validation
        if medicine.get('expiry_date'):
            try:
                expiry = datetime.strptime(medicine['expiry_date'], '%Y-%m-%d')
                days_until_expiry = (expiry - datetime.now()).days
                
                # VALIDATE DATE RANGE
                if days_until_expiry < -30:
                    # Already expired over a month ago
                    revenue_loss = quantity * estimated_price
                    alert = {
                        'alert_id': f"expired_{medicine_id}_{timestamp}",
                        'type': 'expired_medicine',
                        'severity': 'high',
                        'medicine_name': medicine['name'],
                        'expiry_date': medicine['expiry_date'],
                        'days_past_expiry': abs(days_until_expiry),
                        'revenue_loss': revenue_loss,
                        'created_at': timestamp,
                        'resolved': False,
                        'message': f"🚨 {medicine['name']} ALREADY EXPIRED {abs(days_until_expiry)} days ago! Remove immediately. Loss: ₹{revenue_loss}"
                    }
                    alerts_table.put_item(Item=alert)
                    print(f"🚨 EXPIRED: {medicine['name']} - {abs(days_until_expiry)} days past expiry")
                
                elif days_until_expiry > 3650:
                    # More than 10 years - likely OCR error
                    print(f"⚠️ Suspicious expiry date for {medicine['name']}: {medicine['expiry_date']} (too far in future)")
                
                elif days_until_expiry <= 60:
                    # NORMAL EXPIRY WARNING
                    revenue_risk = quantity * estimated_price
                    alert_msg = f"{medicine['name']} expires in {days_until_expiry} days."
                    
                    if revenue_risk > 0:
                        alert_msg += f" 💰 POTENTIAL LOSS: ₹{revenue_risk}"

                    alert = {
                        'alert_id': f"expiry_{medicine_id}_{timestamp}",
                        'type': 'expiry_warning',
                        'severity': 'high' if days_until_expiry <= 30 else 'medium',
                        'medicine_name': medicine['name'],
                        'expiry_date': medicine['expiry_date'],
                        'days_remaining': days_until_expiry,
                        'revenue_risk': revenue_risk,
                        'created_at': timestamp,
                        'resolved': False,
                        'message': alert_msg
                    }
                    alerts_table.put_item(Item=alert)
                    print(f"⚠️ EXPIRY ALERT: {medicine['name']} - {days_until_expiry} days remaining")
            
            except ValueError as e:
                print(f"⚠️ Invalid expiry date format for {medicine['name']}: {medicine['expiry_date']}")
            except Exception as e:
                print(f"⚠️ Error processing expiry for {medicine['name']}: {e}")
    
    # MISSING ESSENTIALS ALERTS
    alert_count = 0
    if analysis_result.get('missing_essentials'):
        for missing in analysis_result['missing_essentials']:
            alert = {
                'alert_id': f"missing_{missing.replace(' ', '_')}_{timestamp}",
                'type': 'missing_essential',
                'severity': 'medium',
                'medicine_name': missing,
                'created_at': timestamp,
                'resolved': False,
                'message': f"⚠️ Essential medicine {missing} is out of stock"
            }
            alerts_table.put_item(Item=alert)
            alert_count += 1
    
    return {
        'medicines_saved': saved_count,
        'medicines_skipped_low_confidence': skipped_count,
        'alerts_created': alert_count,
        'confidence_threshold': MIN_CONFIDENCE_THRESHOLD
    }


def lambda_handler(event, context):
    """
    Lambda handler with enhanced error handling and logging
    """
    try:
        # Parse event body
        if 'body' in event:
             if isinstance(event['body'], str):
                body = json.loads(event['body'])
             else:
                body = event['body']
        else:
            body = event

        # Get S3 bucket and key
        if 'bucket' in body:
            s3_bucket = body['bucket']
            s3_key = body['key']
        elif 'Records' in event:
            s3_bucket = event['Records'][0]['s3']['bucket']['name']
            s3_key = event['Records'][0]['s3']['object']['key']
        else:
            raise ValueError("Could not find bucket/key in event")
        
        print(f"🔍 Processing image: s3://{s3_bucket}/{s3_key}")
        
        # Get image from S3
        s3_object = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        image_bytes = s3_object['Body'].read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        print(f"📊 Image size: {len(image_bytes)} bytes")
        
        # Analyze with Bedrock
        print("🤖 Calling Bedrock Nova Pro...")
        analysis_result = analyze_image_with_bedrock(image_base64)
        
        print(f"✅ AI Analysis complete. Detected {len(analysis_result.get('medicines_detected', []))} medicines")
        
        # Save to DynamoDB
        print("💾 Saving to DynamoDB...")
        db_result = save_to_dynamodb(analysis_result, s3_key)
        
        print(f"✅ Saved {db_result['medicines_saved']} medicines, created {db_result['alerts_created']} alerts")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Image analyzed successfully',
                'analysis': analysis_result,
                'database': db_result,
                'summary': {
                    'medicines_detected': len(analysis_result.get('medicines_detected', [])),
                    'medicines_saved': db_result['medicines_saved'],
                    'skipped_low_confidence': db_result['medicines_skipped_low_confidence'],
                    'alerts_created': db_result['alerts_created'],
                    'confidence_threshold': MIN_CONFIDENCE_THRESHOLD
                }
            })
        }
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'error_type': type(e).__name__,
                'message': 'Failed to analyze image'
            })
        }