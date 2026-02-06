# VyaparIQ Medical Edition

An AI-powered inventory and safety management system for medical stores and pharmacies in India.

## Features

- 📸 **Visual Inventory Audit** - Analyze shelf photos to detect medicines and stock levels
- ⏰ **Expiry Date Intelligence** - Automatic expiry tracking with priority alerts
- 📝 **Prescription-to-Order** - Convert handwritten prescriptions to purchase orders
- 🛡️ **Drug Safety Checker** - Detect dangerous drug interactions
- 📊 **Analytics Dashboard** - Real-time insights and revenue impact tracking

## Tech Stack

- **Frontend:** Streamlit (Python)
- **Backend:** AWS Lambda (Python 3.12)
- **AI/ML:** Amazon Bedrock (Claude 3.5 Sonnet)
- **Database:** Amazon DynamoDB
- **Storage:** Amazon S3
- **Infrastructure:** AWS CDK

## Project Structure

```
vyapariq-medical/
├── src/
│   ├── frontend/
│   │   ├── app.py                 # Streamlit main app
│   │   ├── pages/                 # Multi-page app
│   │   └── components/            # Reusable UI components
│   ├── lambda/
│   │   ├── analyze_shelf/         # Shelf image analysis
│   │   ├── process_expiry/        # Expiry monitoring
│   │   ├── check_interactions/    # Drug safety checker
│   │   └── generate_order/        # Prescription processing
│   ├── utils/
│   │   ├── bedrock_client.py      # Bedrock API wrapper
│   │   ├── dynamodb_client.py     # DynamoDB operations
│   │   └── prompts.py             # AI prompts
│   └── data/
│       ├── drug_interactions.json # Drug interaction database
│       └── essential_medicines.json
├── infrastructure/
│   └── cdk/                       # AWS CDK stack
├── tests/
│   ├── test_images/               # Sample shelf/prescription photos
│   └── unit/                      # Unit tests
├── requirements.txt
├── requirements.md
├── design.md
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.12+
- AWS Account with Free Tier
- AWS CLI configured
- Node.js (for AWS CDK)

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd vyapariq-medical
```

2. Install Python dependencies
```bash
pip install -r requirements.txt
```

3. Configure AWS credentials
```bash
aws configure
```

4. Deploy infrastructure
```bash
cd infrastructure/cdk
cdk deploy
```

5. Run Streamlit app
```bash
streamlit run src/frontend/app.py
```

## Usage

### 1. Analyze Shelf
- Navigate to "Inventory Audit" page
- Upload shelf photo
- View detected medicines and stock levels

### 2. Check Expiry Dates
- Go to "Expiry Monitor" page
- View color-coded alerts (Red/Yellow/Green)
- Take action on expiring medicines

### 3. Process Prescription
- Upload handwritten prescription photo
- Review extracted medicines
- Generate purchase order

### 4. Safety Check
- Enter medicines being restocked
- View interaction warnings
- Get safety recommendations

## Testing

Run unit tests:
```bash
pytest tests/
```

Test with sample images:
```bash
python tests/test_shelf_analysis.py
```

## Cost Estimation

- Lambda: Free (within 1M requests/month)
- DynamoDB: Free (within 25GB)
- S3: Free (within 5GB)
- Bedrock: ~$0.01 per image analysis
- **Total:** <$5 for hackathon demo

## Limitations

- Uses synthetic test data
- OCR accuracy depends on image quality
- Simplified drug interaction database
- Basic Hindi language support
- No billing software integration

## Future Roadmap

- [ ] Voice interface for low-literacy users
- [ ] Barcode scanning
- [ ] Mobile app (React Native)
- [ ] Government drug price API integration
- [ ] Predictive demand analytics

## License

MIT License

## Contributors

Built for AWS AI for Bharat Hackathon

## Support

For issues and questions, please open a GitHub issue.