# VyaparIQ Medical Edition - Deployment Guide

## Prerequisites

### 1. AWS Account Setup
- Create an AWS account (Free Tier eligible)
- Configure AWS CLI with credentials
- Enable Amazon Bedrock access in your region

### 2. Local Development Environment
- Python 3.12 or higher
- Node.js 18+ (for AWS CDK)
- AWS CLI v2
- Git

## Step-by-Step Deployment

### Step 1: Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd vyapariq-medical

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Enter your credentials:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: us-east-1
# Default output format: json
```

### Step 3: Enable Amazon Bedrock

1. Go to AWS Console → Amazon Bedrock
2. Navigate to "Model access"
3. Request access to "Claude 3.5 Sonnet"
4. Wait for approval (usually instant for Free Tier)

### Step 4: Deploy Infrastructure with CDK

```bash
# Navigate to CDK directory
cd infrastructure/cdk

# Install CDK dependencies
pip install -r requirements.txt

# Install AWS CDK CLI globally
npm install -g aws-cdk

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy stack
cdk deploy

# Note the outputs:
# - AnalyzeShelfURL
# - CheckInteractionsURL
# - GenerateOrderURL
# - ShelfImagesBucket
# - PrescriptionsBucket
```

### Step 5: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your values from CDK outputs
# Update:
# - Lambda Function URLs
# - S3 Bucket names
# - DynamoDB table names
```

### Step 6: Run Streamlit Application

```bash
# Navigate back to project root
cd ../..

# Run Streamlit app
streamlit run src/frontend/app.py

# App will open at http://localhost:8501
```

## Testing the Deployment

### Test 1: Shelf Image Analysis

1. Navigate to "Inventory Audit" page
2. Upload a test shelf image
3. Click "Analyze Shelf"
4. Verify medicines are detected

### Test 2: Expiry Monitoring

1. Manually add test data to DynamoDB Inventory table
2. Run the process_expiry Lambda function manually
3. Check Alerts table for created alerts
4. View alerts in "Expiry Monitor" page

### Test 3: Prescription Processing

1. Navigate to "Prescription Upload" page
2. Upload a test prescription image
3. Click "Process Prescription"
4. Verify medicines are extracted

### Test 4: Drug Interaction Check

1. Navigate to "Safety Checker" page
2. Enter: "Aspirin" and "Warfarin"
3. Click "Check Interactions"
4. Verify critical interaction warning appears

## Cost Monitoring

### Expected Costs (Free Tier)

- **Lambda**: Free (1M requests/month)
- **DynamoDB**: Free (25GB storage, 25 RCU/WCU)
- **S3**: Free (5GB storage, 20K GET, 2K PUT)
- **Bedrock**: ~$0.003 per image analysis
  - 100 images = ~$0.30
  - 1000 images = ~$3.00

### Monitor Costs

```bash
# Check AWS billing dashboard
aws ce get-cost-and-usage \
  --time-period Start=2024-02-01,End=2024-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

## Troubleshooting

### Issue: Bedrock Access Denied

**Solution:**
1. Go to AWS Console → Bedrock
2. Request model access
3. Wait for approval
4. Redeploy Lambda functions

### Issue: Lambda Timeout

**Solution:**
1. Increase timeout in CDK stack
2. Optimize image size (compress before upload)
3. Use smaller Bedrock model (Haiku instead of Sonnet)

### Issue: DynamoDB Throttling

**Solution:**
1. Switch to on-demand billing mode (already configured)
2. Add exponential backoff in code
3. Batch write operations

### Issue: S3 Upload Fails

**Solution:**
1. Check bucket permissions
2. Verify CORS configuration
3. Check file size (<5MB recommended)

## Production Deployment

### Additional Steps for Production

1. **Custom Domain**
   ```bash
   # Add Route53 and CloudFront
   # Update CDK stack with domain configuration
   ```

2. **Authentication**
   ```bash
   # Add Cognito user pool
   # Update Lambda function URLs to use IAM auth
   ```

3. **Monitoring**
   ```bash
   # Set up CloudWatch alarms
   # Configure SNS notifications
   # Enable X-Ray tracing
   ```

4. **Backup**
   ```bash
   # Enable DynamoDB point-in-time recovery
   # Configure S3 versioning
   # Set up automated backups
   ```

5. **CI/CD Pipeline**
   ```bash
   # Set up GitHub Actions
   # Automate CDK deployments
   # Add automated testing
   ```

## Cleanup

### Remove All Resources

```bash
# Navigate to CDK directory
cd infrastructure/cdk

# Destroy stack
cdk destroy

# Confirm deletion when prompted
# This will remove:
# - All Lambda functions
# - DynamoDB tables
# - S3 buckets (and contents)
# - IAM roles
# - EventBridge rules
```

### Verify Cleanup

```bash
# Check for remaining resources
aws cloudformation list-stacks \
  --stack-status-filter DELETE_COMPLETE

# Check S3 buckets
aws s3 ls | grep vyapariq

# Check DynamoDB tables
aws dynamodb list-tables | grep VyaparIQ
```

## Support

For issues and questions:
- Check AWS CloudWatch Logs
- Review Lambda function logs
- Open GitHub issue
- Contact AWS Support (if needed)

## Next Steps

1. Add more test data
2. Create synthetic shelf images
3. Build mobile app interface
4. Integrate with pharmacy billing software
5. Add voice interface
6. Implement barcode scanning
