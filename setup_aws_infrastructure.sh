#!/bin/bash

# VyaparIQ Medical - AWS Infrastructure Setup Script
# Run this script to create all required AWS resources

set -e  # Exit on error

echo "🚀 VyaparIQ Medical - AWS Setup Starting..."

# Configuration
REGION="us-east-1"
S3_BUCKET="vyapariq-medical-images-$(date +%s)"  # Unique bucket name
LAMBDA_ROLE="VyaparIQ-Lambda-Role"

echo "📍 Using AWS Region: $REGION"
echo "📦 S3 Bucket will be: $S3_BUCKET"

# 1. Create S3 Bucket for images
echo ""
echo "📦 Step 1: Creating S3 Bucket..."
aws s3 mb s3://$S3_BUCKET --region $REGION

# Enable S3 event notifications (will configure later)
echo "✅ S3 Bucket created: $S3_BUCKET"

# 2. Create DynamoDB Tables
echo ""
echo "🗄️  Step 2: Creating DynamoDB Tables..."

# Inventory Table
echo "Creating Inventory table..."
aws dynamodb create-table \
    --table-name VyaparIQ-Inventory \
    --attribute-definitions \
        AttributeName=medicine_id,AttributeType=S \
    --key-schema \
        AttributeName=medicine_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

# Alerts Table
echo "Creating Alerts table..."
aws dynamodb create-table \
    --table-name VyaparIQ-Alerts \
    --attribute-definitions \
        AttributeName=alert_id,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
    --key-schema \
        AttributeName=alert_id,KeyType=HASH \
    --global-secondary-indexes \
        "IndexName=CreatedAtIndex,KeySchema=[{AttributeName=created_at,KeyType=HASH}],Projection={ProjectionType=ALL}" \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

# Purchase Orders Table
echo "Creating PurchaseOrders table..."
aws dynamodb create-table \
    --table-name VyaparIQ-PurchaseOrders \
    --attribute-definitions \
        AttributeName=order_id,AttributeType=S \
    --key-schema \
        AttributeName=order_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

echo "✅ DynamoDB tables created"

# 3. Create IAM Role for Lambda
echo ""
echo "🔐 Step 3: Creating IAM Role for Lambda..."

# Create trust policy
cat > /tmp/lambda-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
    --role-name $LAMBDA_ROLE \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --region $REGION || echo "Role may already exist"

# Attach policies
echo "Attaching policies to Lambda role..."
aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Create inline policy for Bedrock access
cat > /tmp/bedrock-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name $LAMBDA_ROLE \
    --policy-name BedrockAccess \
    --policy-document file:///tmp/bedrock-policy.json

echo "✅ IAM Role configured"

# 4. Wait for tables to become active
echo ""
echo "⏳ Step 4: Waiting for DynamoDB tables to become active..."
aws dynamodb wait table-exists --table-name VyaparIQ-Inventory --region $REGION
aws dynamodb wait table-exists --table-name VyaparIQ-Alerts --region $REGION
aws dynamodb wait table-exists --table-name VyaparIQ-PurchaseOrders --region $REGION
echo "✅ All tables are active"

# 5. Save configuration
echo ""
echo "💾 Step 5: Saving configuration..."
cat > config.env << EOF
# VyaparIQ Medical Configuration
# Generated on $(date)

AWS_REGION=$REGION
S3_BUCKET=$S3_BUCKET
LAMBDA_ROLE=$LAMBDA_ROLE
INVENTORY_TABLE=VyaparIQ-Inventory
ALERTS_TABLE=VyaparIQ-Alerts
PURCHASE_ORDERS_TABLE=VyaparIQ-PurchaseOrders
EOF

echo "✅ Configuration saved to config.env"

# Summary
echo ""
echo "======================================"
echo "🎉 AWS Infrastructure Setup Complete!"
echo "======================================"
echo ""
echo "📋 Summary:"
echo "  S3 Bucket: $S3_BUCKET"
echo "  Region: $REGION"
echo "  DynamoDB Tables: VyaparIQ-Inventory, VyaparIQ-Alerts, VyaparIQ-PurchaseOrders"
echo "  IAM Role: $LAMBDA_ROLE"
echo ""
echo "📝 Next Steps:"
echo "  1. Source the config: source config.env"
echo "  2. Deploy Lambda functions: ./deploy_lambda.sh"
echo "  3. Test with sample images"
echo ""
