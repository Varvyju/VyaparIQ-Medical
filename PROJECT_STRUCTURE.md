# VyaparIQ Medical Edition - Project Structure

## Complete Directory Tree

```
vyapariq-medical/
│
├── README.md                          # Project overview and setup
├── requirements.md                    # Detailed requirements document
├── design.md                          # System design and architecture
├── DEPLOYMENT.md                      # Deployment guide
├── HACKATHON_SUBMISSION.md           # Hackathon submission document
├── PROJECT_STRUCTURE.md              # This file
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
│
├── src/                               # Source code
│   ├── __init__.py
│   │
│   ├── frontend/                      # Streamlit web application
│   │   ├── __init__.py
│   │   └── app.py                     # Main Streamlit app
│   │
│   ├── lambda/                        # AWS Lambda functions
│   │   ├── __init__.py
│   │   ├── analyze_shelf/            # Shelf image analysis
│   │   │   └── lambda_function.py
│   │   ├── process_expiry/           # Expiry date monitoring
│   │   │   └── lambda_function.py
│   │   ├── check_interactions/       # Drug safety checker
│   │   │   └── lambda_function.py
│   │   └── generate_order/           # Prescription processing
│   │       └── lambda_function.py
│   │
│   ├── utils/                         # Utility modules
│   │   ├── __init__.py
│   │   ├── bedrock_client.py         # Amazon Bedrock API wrapper
│   │   ├── dynamodb_client.py        # DynamoDB operations
│   │   └── prompts.py                # AI prompt templates
│   │
│   └── data/                          # Data files
│       ├── drug_interactions.json    # Drug interaction database
│       └── essential_medicines.json  # Essential medicines list
│
├── infrastructure/                    # Infrastructure as Code
│   └── cdk/                          # AWS CDK
│       ├── app.py                    # CDK app entry point
│       ├── cdk.json                  # CDK configuration
│       ├── requirements.txt          # CDK dependencies
│       └── stacks/
│           ├── __init__.py
│           └── vyapariq_stack.py    # Main CDK stack
│
└── tests/                            # Test files
    ├── __init__.py
    ├── test_bedrock_client.py       # Bedrock client tests
    ├── test_dynamodb_client.py      # DynamoDB client tests
    └── test_images/                 # Sample test images
        └── README.md                # Instructions for test images
```

## File Descriptions

### Root Level Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview, features, setup instructions |
| `requirements.md` | Detailed functional and non-functional requirements |
| `design.md` | System architecture, data schemas, API endpoints |
| `DEPLOYMENT.md` | Step-by-step deployment guide for AWS |
| `HACKATHON_SUBMISSION.md` | Hackathon submission document |
| `requirements.txt` | Python package dependencies |
| `.env.example` | Template for environment variables |
| `.gitignore` | Files and directories to ignore in Git |

### Source Code (`src/`)

#### Frontend (`src/frontend/`)
- **`app.py`**: Main Streamlit application with 5 pages:
  - Dashboard: Overview and metrics
  - Inventory Audit: Shelf image analysis
  - Expiry Monitor: Expiry date tracking
  - Prescription Upload: Prescription processing
  - Safety Checker: Drug interaction validation

#### Lambda Functions (`src/lambda/`)
- **`analyze_shelf/`**: Analyzes shelf images using Bedrock
  - Triggered by S3 upload or API call
  - Updates DynamoDB inventory
  
- **`process_expiry/`**: Daily expiry monitoring
  - Scheduled via EventBridge (6 AM IST)
  - Creates alerts for expiring medicines
  
- **`check_interactions/`**: Drug safety validation
  - Called via API
  - Uses Bedrock for interaction analysis
  
- **`generate_order/`**: Prescription OCR
  - Processes prescription images
  - Creates purchase orders in DynamoDB

#### Utilities (`src/utils/`)
- **`bedrock_client.py`**: Wrapper for Amazon Bedrock API
  - Methods: analyze_shelf_image, process_prescription, check_drug_interactions
  - Handles JSON parsing and error handling
  
- **`dynamodb_client.py`**: DynamoDB operations
  - CRUD operations for inventory, alerts, orders
  - Query methods for expiring medicines, low stock
  
- **`prompts.py`**: AI prompt templates
  - Structured prompts for consistent JSON outputs
  - Handles Indian pharmaceutical context

#### Data (`src/data/`)
- **`drug_interactions.json`**: 20 common drug interactions
  - Severity levels: CRITICAL, HIGH, MODERATE, LOW
  - Recommendations for each interaction
  
- **`essential_medicines.json`**: 30 essential medicines
  - Common Indian brands
  - Reorder levels and priorities

### Infrastructure (`infrastructure/`)

#### CDK (`infrastructure/cdk/`)
- **`app.py`**: CDK application entry point
- **`vyapariq_stack.py`**: Main infrastructure stack
  - DynamoDB tables (3)
  - S3 buckets (2)
  - Lambda functions (4)
  - EventBridge rules
  - IAM roles and policies
  - Lambda Function URLs

### Tests (`tests/`)
- **`test_bedrock_client.py`**: Unit tests for Bedrock client
- **`test_dynamodb_client.py`**: Unit tests for DynamoDB client
- **`test_images/`**: Sample images for testing

## Data Flow

### 1. Shelf Image Analysis Flow
```
User uploads image → Streamlit
                    ↓
                S3 Bucket
                    ↓
        Lambda (analyze_shelf)
                    ↓
        Bedrock (Claude 3.5)
                    ↓
        DynamoDB (Inventory)
                    ↓
        Streamlit Dashboard
```

### 2. Expiry Monitoring Flow
```
EventBridge (Daily 6 AM)
            ↓
Lambda (process_expiry)
            ↓
DynamoDB (Inventory) → Scan
            ↓
Calculate expiry dates
            ↓
DynamoDB (Alerts) → Create
            ↓
Streamlit Dashboard
```

### 3. Prescription Processing Flow
```
User uploads prescription → Streamlit
                           ↓
                    S3 Bucket
                           ↓
            Lambda (generate_order)
                           ↓
            Bedrock (OCR)
                           ↓
    Lambda (check_interactions)
                           ↓
        DynamoDB (Orders)
                           ↓
        Streamlit Dashboard
```

## Technology Stack

### Frontend
- **Streamlit**: Python web framework
- **Pillow**: Image processing
- **Pandas**: Data manipulation

### Backend
- **AWS Lambda**: Serverless compute
- **Python 3.12**: Runtime
- **boto3**: AWS SDK

### AI/ML
- **Amazon Bedrock**: AI service
- **Claude 3.5 Sonnet**: Vision + reasoning
- **Prompt Engineering**: Structured outputs

### Database
- **Amazon DynamoDB**: NoSQL database
- **On-demand pricing**: Auto-scaling

### Storage
- **Amazon S3**: Object storage
- **Lifecycle policies**: Auto-deletion

### Infrastructure
- **AWS CDK**: Infrastructure as Code
- **Python**: CDK language
- **CloudFormation**: Underlying service

## Environment Variables

Required environment variables (see `.env.example`):

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

S3_SHELF_IMAGES_BUCKET=vyapariq-shelf-images
S3_PRESCRIPTIONS_BUCKET=vyapariq-prescriptions

DYNAMODB_INVENTORY_TABLE=VyaparIQ-Inventory
DYNAMODB_ALERTS_TABLE=VyaparIQ-Alerts
DYNAMODB_ORDERS_TABLE=VyaparIQ-PurchaseOrders

BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

LAMBDA_ANALYZE_SHELF_URL=https://...
LAMBDA_CHECK_INTERACTIONS_URL=https://...
LAMBDA_GENERATE_ORDER_URL=https://...
```

## Key Dependencies

### Python Packages
- `streamlit==1.31.0` - Web framework
- `boto3==1.34.34` - AWS SDK
- `Pillow==10.2.0` - Image processing
- `pandas==2.2.0` - Data manipulation
- `pytest==8.0.0` - Testing

### CDK Packages
- `aws-cdk-lib==2.120.0` - CDK library
- `constructs>=10.0.0` - CDK constructs

## Development Workflow

1. **Local Development**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   streamlit run src/frontend/app.py
   ```

2. **Testing**
   ```bash
   pytest tests/
   ```

3. **Deploy Infrastructure**
   ```bash
   cd infrastructure/cdk
   cdk deploy
   ```

4. **Update Lambda Functions**
   ```bash
   # Make changes to src/lambda/
   cdk deploy  # Redeploys with new code
   ```

## File Sizes (Approximate)

- Total project: ~50 KB (code only)
- With dependencies: ~200 MB
- CDK deployment: ~5 MB
- Lambda deployment packages: ~10 MB each

## Next Steps

1. Add test images to `tests/test_images/`
2. Configure AWS credentials
3. Deploy infrastructure with CDK
4. Run Streamlit app locally
5. Test all features
6. Deploy to production

## Support

For questions about the project structure:
- Check README.md for overview
- Check DEPLOYMENT.md for setup
- Check design.md for architecture
- Open GitHub issue for bugs
