# VyaparIQ Medical Edition - System Design Document

## Architecture Overview

### Architecture Pattern
**Serverless Event-Driven Architecture**

```
[Streamlit Frontend] 
        ↓
    [S3 Bucket] → [Lambda Functions] → [Amazon Bedrock]
        ↓                ↓                      ↓
   [Images]      [DynamoDB Tables]    [Knowledge Base (RAG)]
```

## Component Architecture

### 1. Frontend Layer
**Technology:** Streamlit (Python web app)
- Runs locally or on AWS Lightsail for demo
- Mobile-responsive CSS
- Camera integration for photo capture
- Real-time dashboard updates

**Key Features:**
- Image upload interface
- Inventory grid view (color-coded)
- Expiry calendar
- Alert notifications
- Purchase order generation

### 2. Backend Layer
**Technology:** AWS Lambda (Python 3.12)

**Lambda Functions:**
1. **analyze_shelf_image** - Triggered by S3 upload
2. **process_expiry_dates** - Scheduled daily scan
3. **check_drug_interactions** - Called on restock event
4. **generate_purchase_order** - Triggered by prescription upload

### 3. AI/ML Layer
**Amazon Bedrock - Claude 3.5 Sonnet**
- Multimodal vision + reasoning capabilities
- Structured JSON output for medicine extraction
- Prompt engineering for accurate OCR

**Amazon Bedrock Knowledge Base**
- RAG for drug interaction data
- Vector embeddings for medicine matching

### 4. Data Storage Layer

#### Amazon S3
**Buckets:**
- `vyapariq-shelf-images` - Store shelf photos
- `vyapariq-prescriptions` - Store prescription images
- Lifecycle policy: Delete after 24 hours

#### Amazon DynamoDB
**Tables:**

**Inventory Table**
```json
{
  "medicine_id": "MED001",
  "name": "Paracetamol 500mg",
  "brand": "Dolo",
  "stock_count": 150,
  "reorder_level": 50,
  "expiry_date": "2025-12-31",
  "last_updated": "2024-02-06T10:30:00Z",
  "shelf_location": "A1",
  "price": 2.50,
  "supplier": "Cipla"
}
```

**Alerts Table**
```json
{
  "alert_id": "ALERT001",
  "type": "EXPIRY_WARNING",
  "severity": "HIGH",
  "medicine_id": "MED001",
  "message": "Paracetamol expires in 25 days",
  "created_at": "2024-02-06T10:30:00Z",
  "resolved": false,
  "days_until_expiry": 25
}
```

**PurchaseOrders Table**
```json
{
  "order_id": "PO001",
  "items": [
    {
      "medicine_name": "Amoxicillin 250mg",
      "quantity": 100,
      "generic_alternative": "Novamox"
    }
  ],
  "status": "PENDING",
  "created_at": "2024-02-06T10:30:00Z",
  "total_amount": 500.00
}
```

### 5. Integration Layer
- **AWS Lambda Function URLs** - For API endpoints (no API Gateway needed)
- **boto3 SDK** - AWS service communication
- **EventBridge** - Scheduled triggers for daily scans

## Data Flow

### Flow 1: Shelf Image Analysis
1. User uploads shelf photo via Streamlit → S3 bucket (with event notification)
2. S3 triggers `analyze_shelf_image` Lambda
3. Lambda downloads image, converts to base64
4. Lambda calls Bedrock with structured prompt
5. Bedrock returns JSON with detected medicines
6. Lambda parses and upserts to DynamoDB Inventory table
7. Lambda returns analysis to Streamlit
8. UI displays color-coded inventory grid

### Flow 2: Expiry Monitoring
1. EventBridge triggers `process_expiry_dates` Lambda daily at 6 AM
2. Lambda scans DynamoDB Inventory table
3. Calculates days until expiry for each medicine
4. Creates alerts for medicines expiring within 30/60/90 days
5. Inserts alerts into Alerts table
6. Sends notification to dashboard

### Flow 3: Prescription Processing
1. User uploads prescription photo → S3
2. S3 triggers `generate_purchase_order` Lambda
3. Lambda calls Bedrock for OCR extraction
4. Lambda calls `check_drug_interactions` for safety check
5. Lambda creates purchase order in DynamoDB
6. Returns order with safety warnings to UI

## Prompt Engineering Strategy

### Shelf Analysis Prompt
```
You are an expert pharmacist analyzing a medical store shelf. 
Return ONLY valid JSON (no markdown):

{
  "medicines_detected": [
    {
      "name": "Paracetamol 500mg",
      "brand": "Dolo",
      "quantity_estimate": 15,
      "expiry_visible": false
    }
  ],
  "missing_essentials": ["Insulin", "ORS packets"],
  "shelf_condition": "organized",
  "confidence_score": 0.92
}

Be conservative in quantity estimates. If you can't read a label clearly, 
mark confidence as low.
```

### Prescription OCR Prompt
```
Extract medicine information from this handwritten prescription.
Handle common abbreviations:
- Tab = Tablets
- Cap = Capsules
- Syr = Syrup

Return JSON:
{
  "medicines": [
    {
      "name": "Paracetamol",
      "dosage": "500mg",
      "form": "Tablet",
      "quantity": 10,
      "frequency": "3 times daily"
    }
  ],
  "doctor_name": "Dr. Sharma",
  "date": "2024-02-06"
}
```

## API Endpoints (Lambda Function URLs)

### 1. Analyze Shelf
```
POST /analyze-shelf
Content-Type: application/json

Request:
{
  "image_key": "shelf_photos/IMG_001.jpg",
  "store_id": "STORE001"
}

Response:
{
  "status": "success",
  "medicines_detected": [...],
  "missing_essentials": [...],
  "processing_time": 2.3
}
```

### 2. Get Alerts
```
GET /alerts?severity=HIGH&resolved=false

Response:
{
  "alerts": [
    {
      "alert_id": "ALERT001",
      "type": "EXPIRY_WARNING",
      "message": "Paracetamol expires in 25 days",
      "severity": "HIGH"
    }
  ]
}
```

### 3. Check Drug Interactions
```
POST /check-interactions
Content-Type: application/json

Request:
{
  "medicines": ["Aspirin", "Warfarin"]
}

Response:
{
  "status": "warning",
  "interactions": [
    {
      "drug1": "Aspirin",
      "drug2": "Warfarin",
      "severity": "CRITICAL",
      "description": "Increased bleeding risk",
      "recommendation": "Avoid combination"
    }
  ]
}
```

## Security Architecture

### Authentication
- API key-based authentication for Lambda function URLs
- IAM roles with least privilege access

### Data Protection
- S3 bucket encryption at rest
- TLS 1.3 for data in transit
- No PII storage
- Image auto-deletion after 24 hours

### Compliance
- Disclaimer: "This is an inventory management tool, not medical advice"
- No real patient data
- Synthetic test data only

## Scalability Considerations

### Current (Demo)
- Lambda: 128MB memory, 30s timeout
- DynamoDB: On-demand pricing
- S3: Standard storage class

### Future (Production)
- DynamoDB auto-scaling
- S3 + CloudFront for image delivery
- Bedrock batch processing for bulk uploads
- Lambda reserved concurrency

## Cost Optimization

### AWS Free Tier Usage
- Lambda: 1M requests/month free
- DynamoDB: 25GB storage free
- S3: 5GB storage free
- Bedrock: Pay per token (optimize prompts)

### Target Cost
- <$5 for entire hackathon
- <₹2 per 100 API calls in production

## Testing Strategy

### Test Data
- 10 synthetic shelf photos (Canva/Google Images)
- 5 sample prescription images (handwritten test cases)
- Mock drug interaction database (20 common drug pairs)

### Test Scenarios
1. Clear shelf photo with 10 medicines
2. Partially visible labels
3. Regional language packaging
4. Handwritten prescription with abbreviations
5. Drug interaction check with known pairs

## Monitoring & Observability

### CloudWatch Metrics
- Lambda invocation count
- Lambda error rate
- Bedrock API latency
- DynamoDB read/write capacity

### CloudWatch Logs
- Structured logging for all Lambda functions
- Error tracking and debugging

### Alarms
- Lambda error rate >5%
- Bedrock API throttling
- DynamoDB capacity exceeded

## Deployment Strategy

### Infrastructure as Code
- AWS CDK (Python) for infrastructure deployment
- Separate stacks for dev/prod environments

### CI/CD Pipeline
- GitHub Actions for automated deployment
- Automated testing before deployment
- Rollback capability

## Future Enhancements

### Phase 2
- Voice interface for low-literacy users
- Barcode scanning for faster input
- Mobile app (React Native)

### Phase 3
- Integration with government drug price API
- Supplier integration for automated ordering
- Predictive analytics for demand forecasting