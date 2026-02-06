import json
import boto3
import os
import base64
from datetime import datetime

# Initialize clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

INVENTORY_TABLE = os.environ.get('DYNAMODB_INVENTORY_TABLE', 'VyaparIQ-Inventory')
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

def lambda_handler(event, context):
    """
    Lambda function to analyze shelf images and update inventory
    Triggered by S3 upload event
    """
    
    try:
        # Parse event
        if 'Records' in event:
            # S3 event trigger
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = event['Records'][0]['s3']['object']['key']
            
            # Download image from S3
            response = s3.get_object(Bucket=bucket, Key=key)
            image_bytes = response['Body'].read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
        elif 'body' in event:
            # API Gateway/Function URL trigger
            body = json.loads(event['body'])
            image_base64 = body.get('image_base64')
            
            if not image_base64:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing image_base64 in request'})
                }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event format'})
            }
        
        # Prepare Bedrock prompt
        prompt = """You are an expert pharmacist analyzing a medical store shelf. 
Return ONLY valid JSON (no markdown):

{
  "medicines_detected": [
    {
      "name": "Medicine name with dosage",
      "brand": "Brand name",
      "quantity_estimate": <number>,
      "expiry_visible": true/false,
      "expiry_date": "YYYY-MM-DD" (if visible),
      "confidence_score": <0.0-1.0>
    }
  ],
  "missing_essentials": ["List of common medicines that should be on shelf"],
  "shelf_condition": "organized" | "cluttered" | "needs_restocking",
  "confidence_score": <0.0-1.0>
}

Be conservative in quantity estimates. Focus on Indian pharmaceutical brands."""

        # Call Bedrock
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        bedrock_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": messages,
            "temperature": 0.1
        })
        
        bedrock_response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=bedrock_body
        )
        
        response_body = json.loads(bedrock_response['body'].read())
        content = response_body.get('content', [])
        
        if not content:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'No response from Bedrock'})
            }
        
        # Parse JSON response
        text_content = content[0].get('text', '')
        
        # Remove markdown code blocks if present
        if text_content.startswith('```json'):
            text_content = text_content.replace('```json', '').replace('```', '').strip()
        elif text_content.startswith('```'):
            text_content = text_content.replace('```', '').strip()
        
        analysis_result = json.loads(text_content)
        
        # Update DynamoDB inventory
        table = dynamodb.Table(INVENTORY_TABLE)
        
        for medicine in analysis_result.get('medicines_detected', []):
            medicine_id = f"MED_{medicine['name'].replace(' ', '_')}"
            
            item = {
                'medicine_id': medicine_id,
                'name': medicine['name'],
                'brand': medicine.get('brand', ''),
                'stock_count': medicine.get('quantity_estimate', 0),
                'expiry_date': medicine.get('expiry_date', ''),
                'last_updated': datetime.now().isoformat(),
                'confidence_score': medicine.get('confidence_score', 0.0)
            }
            
            table.put_item(Item=item)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'success',
                'analysis': analysis_result,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to analyze shelf image'
            })
        }
