import boto3
import json
import os
from typing import Dict, List, Optional


class BedrockClient:
    """Client for interacting with Amazon Bedrock API"""

    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )

        self.client = boto3.client(
            service_name="bedrock-runtime", region_name=self.region
        )

    def _invoke_model(self, prompt: str, image_base64: Optional[str] = None) -> Dict:
        """Invoke Bedrock model with text or multimodal input"""

        # Prepare messages
        if image_base64:
            # Multimodal request with image
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
        else:
            # Text-only request
            messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

        # Prepare request body
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages,
                "temperature": 0.1,
                "top_p": 0.9,
            }
        )

        try:
            # Invoke model
            response = self.client.invoke_model(modelId=self.model_id, body=body)

            # Parse response
            response_body = json.loads(response["body"].read())

            # Extract text content
            content = response_body.get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "")

                # Try to parse as JSON
                try:
                    # Remove markdown code blocks if present
                    if text_content.startswith("```json"):
                        text_content = (
                            text_content.replace("```json", "")
                            .replace("```", "")
                            .strip()
                        )
                    elif text_content.startswith("```"):
                        text_content = text_content.replace("```", "").strip()

                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return {"raw_text": text_content}

            return {}

        except Exception as e:
            print(f"Error invoking Bedrock model: {str(e)}")
            return {"error": str(e)}

    def analyze_shelf_image(self, image_base64: str) -> Dict:
        """Analyze medical store shelf image"""

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
  "missing_essentials": ["List of common medicines that should be on shelf but aren't visible"],
  "shelf_condition": "organized" | "cluttered" | "needs_restocking",
  "confidence_score": <0.0-1.0>
}

Be conservative in quantity estimates. If you can't read a label clearly, mark confidence as low.
Focus on identifying Indian pharmaceutical brands like Cipla, Sun Pharma, Dr. Reddy's, etc."""

        return self._invoke_model(prompt, image_base64)

    def process_prescription(self, image_base64: str) -> Dict:
        """Extract medicine information from handwritten prescription"""

        prompt = """Extract medicine information from this handwritten prescription.
Handle common abbreviations:
- Tab = Tablets
- Cap = Capsules
- Syr = Syrup
- Inj = Injection
- mg = milligrams
- ml = milliliters

Return ONLY valid JSON (no markdown):
{
  "medicines": [
    {
      "name": "Medicine name",
      "dosage": "Dosage with unit",
      "form": "Tablet/Capsule/Syrup/Injection",
      "quantity": <number>,
      "frequency": "Dosing frequency (e.g., '3 times daily')",
      "duration": "Treatment duration (e.g., '7 days')"
    }
  ],
  "doctor_name": "Doctor's name if visible",
  "date": "YYYY-MM-DD if visible",
  "patient_age": "Age if mentioned",
  "special_instructions": "Any special notes"
}

If handwriting is unclear, make best effort but mark confidence as low."""

        return self._invoke_model(prompt, image_base64)

    def check_drug_interactions(self, medicines: List[str]) -> Dict:
        """Check for drug interactions using RAG"""

        medicine_list = ", ".join(medicines)

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

        return self._invoke_model(prompt)

    def extract_expiry_dates(self, image_base64: str) -> Dict:
        """Extract expiry dates from medicine packaging"""

        prompt = """Extract expiry dates from medicine strips/bottles in this image.

Return ONLY valid JSON (no markdown):
{
  "medicines": [
    {
      "name": "Medicine name if visible",
      "batch_number": "Batch number if visible",
      "expiry_date": "YYYY-MM-DD",
      "manufacturing_date": "YYYY-MM-DD if visible",
      "confidence": <0.0-1.0>
    }
  ]
}

Look for:
- "EXP", "Expiry", "Use before" labels
- Date formats: MM/YYYY, MM-YYYY, DD/MM/YYYY
- Batch numbers starting with "Batch", "Lot", "B.No"

Be very careful with date parsing - Indian formats often use DD/MM/YYYY."""

        return self._invoke_model(prompt, image_base64)
