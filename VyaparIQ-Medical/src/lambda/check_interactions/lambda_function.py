import json
import boto3
import os

# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

def lambda_handler(event, context):
    """
    Lambda function to check drug interactions
    Called via API when restocking medicines
    """
    
    try:
        # Parse request
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        medicines = body.get('medicines', [])
        
        if not medicines or len(medicines) < 2:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'At least 2 medicines required for interaction check'
                })
            }
        
        medicine_list = ", ".join(medicines)
        
        # Prepare prompt
        prompt = f"""You are a clinical pharmacist checking for drug interactions.

Medicines to check: {medicine_list}

Return ONLY valid JSON (no markdown):
{{
  "status": "safe" | "warning" | "critical",
  "interactions": [
    {{
      "drug1": "First medicine",
      "drug2": "Second medicine",
      "severity": "CRITICAL" | "HIGH" | "MODERATE" | "LOW",
      "description": "Description of interaction",
      "recommendation": "What to do about it"
    }}
  ],
  "overall_assessment": "Summary of safety status"
}}

Common interactions to check:
- Aspirin + Warfarin = Bleeding risk (CRITICAL)
- Paracetamol + Alcohol = Liver damage (HIGH)
- Antibiotics + Antacids = Reduced absorption (MODERATE)
- NSAIDs + ACE inhibitors = Kidney issues (HIGH)

If no interactions found, return empty interactions array."""

        # Call Bedrock
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ]
        
        bedrock_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
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
        
        interaction_result = json.loads(text_content)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'success',
                'medicines_checked': medicines,
                'interaction_analysis': interaction_result
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to check drug interactions'
            })
        }
