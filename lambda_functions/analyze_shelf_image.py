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

def analyze_image_with_bedrock(image_base64):
    """
    Call Bedrock Nova Pro to analyze medical shelf image
    Returns structured JSON of medicines detected
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
    - Estimate quantity by counting visible boxes/strips"""

    # --- NOVA PRO PAYLOAD FORMAT ---
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
    
    # Call Bedrock
    response = bedrock_runtime.invoke_model(
        modelId='amazon.nova-pro-v1:0',
        body=json.dumps(request_body)
    )
    
    # Parse response
    response_body = json.loads(response['body'].read())
    # Nova output structure: output -> message -> content -> text
    ai_response = response_body['output']['message']['content'][0]['text']
    
    # Clean and parse JSON (remove markdown if present)
    ai_response = ai_response.strip()
    if '```json' in ai_response:
        ai_response = ai_response.split('```json')[1].split('```')[0].strip()
    elif '```' in ai_response:
        ai_response = ai_response.split('```')[1].split('```')[0].strip()
    
    return json.loads(ai_response)


def save_to_dynamodb(analysis_result, image_key):
    """
    Save analysis results to DynamoDB
    """
    inventory_table = dynamodb.Table(INVENTORY_TABLE)
    alerts_table = dynamodb.Table(ALERTS_TABLE)
    
    timestamp = datetime.utcnow().isoformat()
    
    # Save each detected medicine to inventory
    medicines = analysis_result.get('medicines_detected', [])
    for medicine in medicines:
        # Create a safe ID
        safe_name = medicine.get('name', 'Unknown').lower().replace(' ', '_')
        safe_brand = medicine.get('brand', 'generic').lower().replace(' ', '_')
        
        inventory_item = {
            'medicine_id': f"{safe_name}_{safe_brand}_{timestamp}", # Unique ID for each scan
            'medicine_name': medicine.get('name', 'Unknown'),
            'brand': medicine.get('brand', 'Unknown'),
            'stock_quantity': medicine.get('quantity_estimate', 0),
            'expiry_date': medicine.get('expiry_date'),
            'confidence': str(medicine.get('confidence', 0.5)), # Convert float to string/decimal for DynamoDB
            'location': medicine.get('location_on_shelf', 'unknown'),
            'last_scanned': timestamp,
            'image_reference': image_key
        }
        
        inventory_table.put_item(Item=inventory_item)
        
        # Create alert if expiry is near (within 60 days)
        if medicine.get('expiry_date'):
            try:
                expiry = datetime.strptime(medicine['expiry_date'], '%Y-%m-%d')
                days_until_expiry = (expiry - datetime.now()).days
                
                if days_until_expiry <= 60:
                    alert = {
                        'alert_id': f"expiry_{safe_name}_{timestamp}",
                        'type': 'expiry_warning',
                        'severity': 'high' if days_until_expiry <= 30 else 'medium',
                        'medicine_name': medicine['name'],
                        'expiry_date': medicine['expiry_date'],
                        'days_remaining': days_until_expiry,
                        'created_at': timestamp,
                        'resolved': False,
                        'message': f"{medicine['name']} expires in {days_until_expiry} days"
                    }
                    alerts_table.put_item(Item=alert)
            except:
                pass # Skip alert if date parsing fails
    
    # Create alert for missing essentials
    if analysis_result.get('missing_essentials'):
        for missing in analysis_result['missing_essentials']:
            alert = {
                'alert_id': f"missing_{missing.replace(' ', '_')}_{timestamp}",
                'type': 'missing_essential',
                'severity': 'medium',
                'medicine_name': missing,
                'created_at': timestamp,
                'resolved': False,
                'message': f"Essential medicine {missing} is out of stock"
            }
            alerts_table.put_item(Item=alert)
    
    # Create alert for low stock
    if analysis_result.get('overall_stock_level') == 'low':
        alert = {
            'alert_id': f"low_stock_{timestamp}",
            'type': 'low_stock_warning',
            'severity': 'low',
            'created_at': timestamp,
            'resolved': False,
            'message': 'Overall shelf stock level is low - consider restocking'
        }
        alerts_table.put_item(Item=alert)
    
    return {
        'medicines_saved': len(medicines),
        'alerts_created': len(analysis_result.get('missing_essentials', []))
    }


def lambda_handler(event, context):
    try:
        # Handle API Gateway event body parsing
        if 'body' in event:
             if isinstance(event['body'], str):
                body = json.loads(event['body'])
             else:
                body = event['body']
        else:
            body = event

        # Handle different event structures (S3 trigger vs Direct invoke)
        if 'bucket' in body:
            s3_bucket = body['bucket']
            s3_key = body['key']
        elif 'Records' in event:
            s3_bucket = event['Records'][0]['s3']['bucket']['name']
            s3_key = event['Records'][0]['s3']['object']['key']
        else:
            raise ValueError("Could not find bucket/key in event")
        
        print(f"Processing image: s3://{s3_bucket}/{s3_key}")
        
        # Download image from S3
        s3_object = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        image_bytes = s3_object['Body'].read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Analyze with Bedrock
        analysis_result = analyze_image_with_bedrock(image_base64)
        
        # Save to DynamoDB
        db_result = save_to_dynamodb(analysis_result, s3_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Image analyzed successfully',
                'analysis': analysis_result,
                'database': db_result
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to analyze image'
            })
        }