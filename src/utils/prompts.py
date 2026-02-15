"""
Prompt templates for Amazon Bedrock interactions
"""

SHELF_ANALYSIS_PROMPT = """You are an expert pharmacist analyzing a medical store shelf. 
Return ONLY valid JSON (no markdown):

{
  "medicines_detected": [
    {
      "name": "Medicine name with dosage (e.g., Paracetamol 500mg)",
      "brand": "Brand name (e.g., Dolo, Crocin)",
      "quantity_estimate": <number of visible units>,
      "expiry_visible": true/false,
      "expiry_date": "YYYY-MM-DD" (if visible),
      "confidence_score": <0.0-1.0>
    }
  ],
  "missing_essentials": ["List of common medicines that should be on shelf but aren't visible"],
  "shelf_condition": "organized" | "cluttered" | "needs_restocking",
  "confidence_score": <0.0-1.0>
}

Guidelines:
- Be conservative in quantity estimates
- If you can't read a label clearly, mark confidence as low
- Focus on identifying Indian pharmaceutical brands (Cipla, Sun Pharma, Dr. Reddy's, etc.)
- Common essential medicines: Paracetamol, Aspirin, ORS, Insulin, Antibiotics
- Look for strip packaging, bottles, and boxes
"""

PRESCRIPTION_OCR_PROMPT = """Extract medicine information from this handwritten prescription.

Handle common abbreviations:
- Tab = Tablets
- Cap = Capsules
- Syr = Syrup
- Inj = Injection
- mg = milligrams
- ml = milliliters
- BD/BID = Twice daily
- TDS/TID = Three times daily
- QID = Four times daily
- OD = Once daily
- SOS = As needed

Return ONLY valid JSON (no markdown):
{
  "medicines": [
    {
      "name": "Medicine name",
      "dosage": "Dosage with unit (e.g., 500mg)",
      "form": "Tablet/Capsule/Syrup/Injection",
      "quantity": <number>,
      "frequency": "Dosing frequency (e.g., '3 times daily', 'BD', 'TDS')",
      "duration": "Treatment duration (e.g., '7 days', '2 weeks')"
    }
  ],
  "doctor_name": "Doctor's name if visible",
  "date": "YYYY-MM-DD if visible",
  "patient_age": "Age if mentioned",
  "special_instructions": "Any special notes (e.g., 'Take after food')"
}

Guidelines:
- If handwriting is unclear, make best effort but mark confidence as low
- Common Indian medicine names: Dolo, Crocin, Combiflam, Azithral, Augmentin
- Look for Rx symbol indicating prescription
- Extract all visible information
"""

DRUG_INTERACTION_PROMPT = """You are a clinical pharmacist checking for drug interactions.

Medicines to check: {medicine_list}

Return ONLY valid JSON (no markdown):
{{
  "status": "safe" | "warning" | "critical",
  "interactions": [
    {{
      "drug1": "First medicine",
      "drug2": "Second medicine",
      "severity": "CRITICAL" | "HIGH" | "MODERATE" | "LOW",
      "description": "Description of interaction and potential effects",
      "recommendation": "What to do about it (e.g., 'Avoid combination', 'Monitor closely')"
    }}
  ],
  "overall_assessment": "Summary of safety status"
}}

Common critical interactions to check:
- Aspirin + Warfarin = Increased bleeding risk (CRITICAL)
- Paracetamol + Alcohol = Liver damage risk (HIGH)
- Antibiotics + Antacids = Reduced absorption (MODERATE)
- NSAIDs + ACE inhibitors = Kidney function issues (HIGH)
- Metformin + Alcohol = Lactic acidosis risk (HIGH)
- Statins + Grapefruit = Increased statin levels (MODERATE)
- MAO inhibitors + Tyramine-rich foods = Hypertensive crisis (CRITICAL)

Guidelines:
- If no interactions found, return empty interactions array
- Consider both drug-drug and drug-food interactions
- Prioritize patient safety
- Provide actionable recommendations
"""

EXPIRY_EXTRACTION_PROMPT = """Extract expiry dates from medicine strips/bottles in this image.

Return ONLY valid JSON (no markdown):
{
  "medicines": [
    {
      "name": "Medicine name if visible",
      "batch_number": "Batch number if visible",
      "expiry_date": "YYYY-MM-DD",
      "manufacturing_date": "YYYY-MM-DD if visible",
      "mrp": "Maximum Retail Price if visible",
      "confidence": <0.0-1.0>
    }
  ]
}

Guidelines:
- Look for "EXP", "Expiry", "Use before", "Best before" labels
- Date formats: MM/YYYY, MM-YYYY, DD/MM/YYYY, DD-MM-YYYY
- Batch numbers: "Batch", "Lot", "B.No", "Mfg.Lic.No"
- Be very careful with date parsing - Indian formats often use DD/MM/YYYY
- If only month/year visible, use last day of that month
- MRP format: "MRP: Rs. XXX" or "M.R.P.: ₹XXX"
"""

GENERIC_ALTERNATIVE_PROMPT = """Suggest generic alternatives for the following branded medicines:

Medicines: {medicine_list}

Return ONLY valid JSON (no markdown):
{{
  "alternatives": [
    {{
      "branded_medicine": "Original branded medicine",
      "generic_name": "Generic/chemical name",
      "alternative_brands": ["List of alternative brands"],
      "price_comparison": {{
        "branded_price": <price>,
        "generic_price": <price>,
        "savings_percent": <percentage>
      }},
      "bioequivalence": "Same efficacy as branded version"
    }}
  ]
}}

Guidelines:
- Focus on Indian pharmaceutical market
- Common generic manufacturers: Cipla, Sun Pharma, Dr. Reddy's, Lupin
- Provide cost-effective alternatives
- Ensure bioequivalence
"""

INVENTORY_INSIGHTS_PROMPT = """Analyze the inventory data and provide actionable insights.

Current inventory: {inventory_data}

Return ONLY valid JSON (no markdown):
{{
  "insights": [
    {{
      "type": "stock_alert" | "expiry_warning" | "reorder_suggestion" | "revenue_opportunity",
      "priority": "HIGH" | "MEDIUM" | "LOW",
      "message": "Clear, actionable insight",
      "affected_medicines": ["List of medicine IDs"],
      "estimated_impact": "Financial or operational impact",
      "recommended_action": "Specific action to take"
    }}
  ],
  "weekly_summary": {{
    "total_medicines": <count>,
    "low_stock_items": <count>,
    "expiring_soon": <count>,
    "estimated_savings": <amount in rupees>,
    "top_recommendations": ["Top 3 actions to take"]
  }}
}}

Guidelines:
- Prioritize patient safety and business profitability
- Consider seasonal demand patterns
- Identify slow-moving stock
- Suggest promotional opportunities for near-expiry items
"""
