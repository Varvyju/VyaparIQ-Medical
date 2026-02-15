import json
import boto3
import base64
import os

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    try:
        # Get bucket and key from event
        body = json.loads(event['body']) if 'body' in event else event
        bucket = body['bucket']
        key = body['key']
        
        # Get image from S3
        response = s3.get_object(Bucket=bucket, Key=key)
        image_content = response['Body'].read()
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        # System prompt for Prescription Processing
        system_prompt = """You are an expert pharmacist AI. Analyze this prescription image and return a JSON response.
        Extract the medicines, dosages, frequencies, and durations.
        Create a purchase order based on this.
        Check for any potential drug interactions between the prescribed medicines.
        
        Return ONLY valid JSON in this format:
        {
            "prescription": {
                "patient_name": "extracted name or null",
                "doctor_name": "extracted name or null",
                "date": "extracted date or null",
                "medicines": [
                    {
                        "medicine_name": "name",
                        "dosage": "e.g. 500mg",
                        "frequency": "e.g. 1-0-1",
                        "duration": "e.g. 5 days",
                        "quantity_needed": 15
                    }
                ]
            },
            "interactions": [
                {
                    "drug1": "name",
                    "drug2": "name",
                    "severity": "high/medium/low",
                    "risk": "description of risk",
                    "recommendation": "advice"
                }
            ],
            "purchase_order": {
                "order_id": "auto-generated",
                "items": [
                    {
                        "medicine_name": "name",
                        "quantity": 15,
                        "form": "tablet/capsule",
                        "estimated_unit_price": 0,
                        "confidence": 0.95
                    }
                ],
                "total_items": 0,
                "status": "pending",
                "created_at": "current_timestamp"
            }
        }
        """

        # NOVA PRO PAYLOAD FORMAT
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
                "max_new_tokens": 2000,
                "temperature": 0.1
            }
        }

        # Invoke Nova Pro
        response = bedrock.invoke_model(
            modelId='amazon.nova-pro-v1:0',
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        # Nova response structure is output -> message -> content -> text
        response_text = response_body['output']['message']['content'][0]['text']
        
        # Parse JSON from AI response
        # Clean up markdown if present
        json_str = response_text.replace('```json', '').replace('```', '').strip()
        result = json.loads(json_str)
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': "Failed to process prescription"
            })
        }