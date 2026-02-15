import json
import boto3
import os
import base64
from datetime import datetime
from decimal import Decimal

# Initialize clients
bedrock_runtime = boto3.client(
    "bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1")
)
dynamodb = boto3.resource(
    "dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1")
)

ORDERS_TABLE = os.environ.get("DYNAMODB_ORDERS_TABLE", "VyaparIQ-PurchaseOrders")
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
)


def lambda_handler(event, context):
    """
    Lambda function to process prescription and generate purchase order
    Triggered by prescription image upload
    """

    try:
        # Parse request
        if "body" in event:
            body = json.loads(event["body"])
        else:
            body = event

        image_base64 = body.get("image_base64")

        if not image_base64:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing image_base64 in request"}),
            }

        # Prepare Bedrock prompt
        prompt = """Extract medicine information from this handwritten prescription.

Handle common abbreviations:
- Tab = Tablets
- Cap = Capsules
- Syr = Syrup
- Inj = Injection
- BD/BID = Twice daily
- TDS/TID = Three times daily

Return ONLY valid JSON (no markdown):
{
  "medicines": [
    {
      "name": "Medicine name",
      "dosage": "Dosage with unit",
      "form": "Tablet/Capsule/Syrup/Injection",
      "quantity": <number>,
      "frequency": "Dosing frequency",
      "duration": "Treatment duration"
    }
  ],
  "doctor_name": "Doctor's name if visible",
  "date": "YYYY-MM-DD if visible",
  "patient_age": "Age if mentioned",
  "special_instructions": "Any special notes"
}

If handwriting is unclear, make best effort."""

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
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        bedrock_body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages,
                "temperature": 0.1,
            }
        )

        bedrock_response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID, body=bedrock_body
        )

        response_body = json.loads(bedrock_response["body"].read())
        content = response_body.get("content", [])

        if not content:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "No response from Bedrock"}),
            }

        # Parse JSON response
        text_content = content[0].get("text", "")

        # Remove markdown code blocks if present
        if text_content.startswith("```json"):
            text_content = (
                text_content.replace("```json", "").replace("```", "").strip()
            )
        elif text_content.startswith("```"):
            text_content = text_content.replace("```", "").strip()

        prescription_data = json.loads(text_content)

        # Create purchase order
        order_id = f"PO_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        order_items = []
        total_amount = 0

        for medicine in prescription_data.get("medicines", []):
            item = {
                "medicine_name": medicine["name"],
                "dosage": medicine.get("dosage", ""),
                "form": medicine.get("form", ""),
                "quantity": medicine.get("quantity", 0),
                "frequency": medicine.get("frequency", ""),
                "duration": medicine.get("duration", ""),
            }
            order_items.append(item)
            # Estimate cost (placeholder - would integrate with pricing API)
            total_amount += medicine.get("quantity", 0) * 10  # ₹10 per unit estimate

        # Save to DynamoDB
        orders_table = dynamodb.Table(ORDERS_TABLE)

        order_item = {
            "order_id": order_id,
            "items": order_items,
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            "total_amount": Decimal(str(total_amount)),
            "doctor_name": prescription_data.get("doctor_name", ""),
            "prescription_date": prescription_data.get("date", ""),
            "special_instructions": prescription_data.get("special_instructions", ""),
        }

        orders_table.put_item(Item=order_item)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "status": "success",
                    "order_id": order_id,
                    "prescription_data": prescription_data,
                    "order_summary": {
                        "total_items": len(order_items),
                        "estimated_amount": total_amount,
                    },
                    "timestamp": datetime.now().isoformat(),
                }
            ),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": str(e), "message": "Failed to process prescription"}
            ),
        }
