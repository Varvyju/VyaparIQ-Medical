# VyaparIQ Medical Edition - System Design Document

## Architecture Overview

### High-Level Architecture
```
[Frontend: Streamlit] -> [API: Lambda Function URL] -> [AI: Amazon Bedrock] -> [DB: DynamoDB]
                                    |
                                    v
                              [Storage: S3]
```

### Component Details

#### Frontend Layer
- **Technology:** Streamlit web application
- **Deployment:** Streamlit Cloud or AWS EC2
- **Features:**
  - Image upload interface
  - Real-time inventory dashboard
  - Alert management system
  - Multi-language support

#### API Layer
- **Technology:** AWS Lambda with Function URLs
- **Runtime:** Python 3.11
- **Features:**
  - RESTful API endpoints
  - Image processing orchestration
  - Authentication and authorization
  - Rate limiting and throttling

#### AI Processing Layer
- **Technology:** Amazon Bedrock
- **Models:**
  - **Claude 3.7 Sonnet:** Complex image analysis, expiry date extraction, safety reasoning
  - **Claude Haiku:** Fast text processing, alert generation, simple queries
- **Features:**
  - Computer vision for shelf analysis
  - OCR for expiry date reading
  - RAG for drug safety validation

#### Data Layer
- **Primary Database:** Amazon DynamoDB
- **File Storage:** Amazon S3
- **Caching:** DynamoDB DAX for high-performance reads

## Data Schema

### DynamoDB Table Structure

#### Main Inventory Table
```json
{
  "PK": "STORE#<store_id>",
  "SK": "PRODUCT#<batch_id>",
  "product_name": "Paracetamol 500mg",
  "manufacturer": "Cipla Ltd",
  "batch_number": "BT2024001",
  "expiry_date": "2025-12-31",
  "quantity": 150,
  "unit_price": 2.50,
  "safety_flag": "SAFE",
  "last_updated": "2024-02-05T10:30:00Z",
  "shelf_location": "A1-Top",
  "drug_code": "PARA500",
  "interactions": ["WARFARIN", "ALCOHOL"]
}
```

#### Alerts Table
```json
{
  "PK": "ALERT#<store_id>",
  "SK": "EXPIRY#<date>",
  "alert_type": "EXPIRY_WARNING",
  "product_batch": "PRODUCT#BT2024001",
  "days_to_expiry": 25,
  "severity": "HIGH",
  "status": "ACTIVE",
  "created_at": "2024-02-05T10:30:00Z"
}
```

#### Safety Database Table
```json
{
  "PK": "DRUG#<drug_code>",
  "SK": "INTERACTION#<interaction_id>",
  "drug_name": "Paracetamol",
  "interacting_drug": "Warfarin",
  "interaction_type": "MAJOR",
  "description": "Increased risk of bleeding",
  "recommendation": "Monitor INR levels closely"
}
```

## API Endpoints

### Core Endpoints

#### 1. Analyze Shelf
```http
POST /analyze-shelf
Content-Type: application/json

Request:
{
  "store_id": "STORE001",
  "image_base64": "<base64_encoded_image>",
  "shelf_id": "A1",
  "timestamp": "2024-02-05T10:30:00Z"
}

Response:
{
  "status": "success",
  "analysis_id": "ANALYSIS_123",
  "detected_products": [
    {
      "product_name": "Paracetamol 500mg",
      "quantity": 45,
      "confidence": 0.95,
      "location": "top-left",
      "status": "LOW_STOCK"
    }
  ],
  "missing_products": [
    {
      "product_name": "Crocin 650mg",
      "expected_location": "middle-right",
      "last_seen": "2024-02-03T14:20:00Z"
    }
  ],
  "processing_time": 2.3
}
```

#### 2. Get Alerts
```http
GET /alerts?store_id=STORE001&type=expiry&days=30

Response:
{
  "status": "success",
  "alerts": [
    {
      "alert_id": "ALERT_456",
      "type": "EXPIRY_WARNING",
      "product": "Amoxicillin 250mg",
      "batch": "BT2024002",
      "expiry_date": "2024-03-01",
      "days_remaining": 25,
      "quantity": 30,
      "severity": "HIGH",
      "recommended_action": "DISCOUNT_SALE"
    }
  ],
  "total_alerts": 1
}
```

#### 3. Safety Check
```http
POST /safety-check
Content-Type: application/json

Request:
{
  "store_id": "STORE001",
  "new_products": [
    {
      "drug_code": "ASPIRIN100",
      "quantity": 100
    }
  ],
  "existing_inventory": true
}

Response:
{
  "status": "success",
  "safety_analysis": {
    "overall_status": "WARNING",
    "interactions_found": [
      {
        "drug1": "Aspirin 100mg",
        "drug2": "Warfarin 5mg",
        "interaction_level": "MAJOR",
        "description": "Increased bleeding risk",
        "recommendation": "Separate storage, add warning labels"
      }
    ],
    "contraindications": []
  }
}
```

## Security Architecture

### Authentication & Authorization
- **API Keys:** Store-specific API keys for Lambda function access
- **IAM Roles:** Least privilege access for all AWS services
- **Encryption:** 
  - Data at rest: DynamoDB and S3 encryption
  - Data in transit: TLS 1.3 for all API calls

### Data Privacy
- **PII Handling:** No personal customer data stored
- **Image Processing:** Images processed in-memory, not permanently stored
- **Audit Logging:** All API calls logged to CloudWatch

## Deployment Architecture

### Infrastructure as Code
- **AWS CDK:** Python-based infrastructure deployment
- **Environment Separation:** Dev, Staging, Production environments
- **CI/CD Pipeline:** GitHub Actions with AWS deployment

### Monitoring & Observability
- **CloudWatch Metrics:** API latency, error rates, Bedrock usage
- **CloudWatch Logs:** Structured logging for debugging
- **X-Ray Tracing:** End-to-end request tracing
- **Custom Dashboards:** Business metrics and system health

## Scalability Considerations

### Performance Optimization
- **Lambda Concurrency:** Reserved concurrency for critical functions
- **DynamoDB Auto-scaling:** Automatic read/write capacity adjustment
- **S3 Transfer Acceleration:** Faster image uploads
- **CloudFront CDN:** Static asset caching

### Cost Optimization
- **Bedrock Model Selection:** Use Haiku for simple tasks, Sonnet for complex analysis
- **Lambda Memory Optimization:** Right-sized memory allocation
- **DynamoDB On-Demand:** Pay-per-request pricing for variable workloads
- **S3 Lifecycle Policies:** Automatic archival of old images

## Future Enhancements

### Phase 2 Features
- **Voice Interface:** Integration with Amazon Polly and Transcribe
- **Mobile App:** React Native application for iOS/Android
- **Advanced Analytics:** Predictive inventory management
- **Integration APIs:** Connect with existing pharmacy management systems

### AI Model Improvements
- **Custom Models:** Fine-tuned models for Indian pharmaceutical products
- **Multi-modal Analysis:** Combine text, image, and voice inputs
- **Federated Learning:** Improve models while maintaining privacy