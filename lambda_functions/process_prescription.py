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
        # ========== HARDCODED CRITICAL INTERACTION CHECK (ADD HERE!) ==========
        # This ensures life-threatening combinations are ALWAYS caught
        # even if the AI misses them
        
        # Convert all medicine names to lowercase for comparison
        medicines_text = json.dumps(result).lower()
        
        # Check for Aspirin + Warfarin (CRITICAL - bleeding risk)
        has_aspirin = 'aspirin' in medicines_text or 'ecosprin' in medicines_text
        has_warfarin = 'warfarin' in medicines_text or 'coumadin' in medicines_text
        
        if has_aspirin and has_warfarin:
            # Initialize interactions list if it doesn't exist
            if 'interactions' not in result:
                result['interactions'] = []
            
            # Check if this interaction is already detected by AI
            already_detected = False
            for interaction in result.get('interactions', []):
                drugs = (interaction.get('drug1', '').lower() + ' ' + 
                        interaction.get('drug2', '').lower())
                if ('aspirin' in drugs or 'ecosprin' in drugs) and \
                   ('warfarin' in drugs or 'coumadin' in drugs):
                    already_detected = True
                    break
            
            # If AI missed it, force add this life-threatening interaction
            if not already_detected:
                result['interactions'].append({
                    'drug1': 'Aspirin',
                    'drug2': 'Warfarin',
                    'severity': 'high',
                    'risk': 'SEVERE BLEEDING RISK - Both medications thin the blood. Combining them can cause life-threatening internal bleeding, bruising, and prolonged bleeding from minor cuts.',
                    'recommendation': 'DO NOT DISPENSE - Contact prescribing physician immediately before dispensing. This combination requires careful monitoring and dose adjustment.'
                })
                print("⚠️ CRITICAL: Aspirin + Warfarin interaction added by safety check!")
        
        # Check for Aspirin + Ibuprofen (MEDIUM - GI bleeding + reduced effectiveness)
        has_ibuprofen = 'ibuprofen' in medicines_text or 'brufen' in medicines_text
        
        if has_aspirin and has_ibuprofen:
            if 'interactions' not in result:
                result['interactions'] = []
            
            # Check if already detected
            already_detected = False
            for interaction in result.get('interactions', []):
                drugs = (interaction.get('drug1', '').lower() + ' ' + 
                        interaction.get('drug2', '').lower())
                if ('aspirin' in drugs or 'ecosprin' in drugs) and \
                   ('ibuprofen' in drugs or 'brufen' in drugs):
                    already_detected = True
                    break
            
            if not already_detected:
                result['interactions'].append({
                    'drug1': 'Aspirin',
                    'drug2': 'Ibuprofen',
                    'severity': 'medium',
                    'risk': 'Increased bleeding risk and stomach ulcers. Ibuprofen can reduce the heart-protective effects of Aspirin.',
                    'recommendation': 'Avoid this combination if possible. Consider alternative pain relief. If both needed, space doses by 8+ hours and take with food.'
                })
                print("⚠️ WARNING: Aspirin + Ibuprofen interaction added by safety check!")
        
        # Add timestamp to purchase order if not present
        if 'purchase_order' in result and result['purchase_order']:
            if 'created_at' not in result['purchase_order'] or \
               result['purchase_order']['created_at'] == 'current_timestamp':
                result['purchase_order']['created_at'] = datetime.utcnow().isoformat()
            
            # Generate order ID if not present
            if 'order_id' not in result['purchase_order'] or \
               result['purchase_order']['order_id'] == 'auto-generated':
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                result['purchase_order']['order_id'] = f"PO_{timestamp}"
        
        # ========== END HARDCODED INTERACTION CHECK ==========
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