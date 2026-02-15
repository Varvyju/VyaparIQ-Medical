#!/bin/bash

# VyaparIQ Medical - Lambda Deployment Script

set -e

echo "🚀 Deploying Lambda Functions..."

# Load configuration
if [ -f config.env ]; then
    source config.env
else
    echo "❌ config.env not found. Run setup_aws_infrastructure.sh first"
    exit 1
fi

cd lambda_functions

# 1. Package and deploy analyze_shelf_image function
echo ""
echo "📦 Packaging analyze_shelf_image function..."
mkdir -p package
pip install -r requirements.txt -t package/ --quiet
cp analyze_shelf_image.py package/
cd package
zip -r ../analyze_shelf_image.zip . -q
cd ..
rm -rf package

echo "☁️  Creating Lambda function: analyze-shelf-image..."
aws lambda create-function \
    --function-name analyze-shelf-image \
    --runtime python3.12 \
    --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):iam::role/$LAMBDA_ROLE \
    --handler analyze_shelf_image.lambda_handler \
    --zip-file fileb://analyze_shelf_image.zip \
    --timeout 60 \
    --memory-size 512 \
    --environment Variables="{INVENTORY_TABLE=VyaparIQ-Inventory,ALERTS_TABLE=VyaparIQ-Alerts}" \
    --region $AWS_REGION || \
    
    # Update if already exists
    aws lambda update-function-code \
        --function-name analyze-shelf-image \
        --zip-file fileb://analyze_shelf_image.zip \
        --region $AWS_REGION

# Create Function URL for direct invocation
echo "Creating Function URL for analyze-shelf-image..."
aws lambda create-function-url-config \
    --function-name analyze-shelf-image \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["POST"],"AllowHeaders":["*"]}' \
    --region $AWS_REGION || echo "Function URL may already exist"

SHELF_FUNCTION_URL=$(aws lambda get-function-url-config --function-name analyze-shelf-image --region $AWS_REGION --query 'FunctionUrl' --output text)

# 2. Package and deploy process_prescription function
echo ""
echo "📦 Packaging process_prescription function..."
mkdir -p package
pip install -r requirements.txt -t package/ --quiet
cp process_prescription.py package/
cd package
zip -r ../process_prescription.zip . -q
cd ..
rm -rf package

echo "☁️  Creating Lambda function: process-prescription..."
aws lambda create-function \
    --function-name process-prescription \
    --runtime python3.12 \
    --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):iam::role/$LAMBDA_ROLE \
    --handler process_prescription.lambda_handler \
    --zip-file fileb://process_prescription.zip \
    --timeout 60 \
    --memory-size 512 \
    --environment Variables="{PURCHASE_ORDERS_TABLE=VyaparIQ-PurchaseOrders,ALERTS_TABLE=VyaparIQ-Alerts}" \
    --region $AWS_REGION || \
    
    aws lambda update-function-code \
        --function-name process-prescription \
        --zip-file fileb://process_prescription.zip \
        --region $AWS_REGION

# Create Function URL
echo "Creating Function URL for process-prescription..."
aws lambda create-function-url-config \
    --function-name process-prescription \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["POST"],"AllowHeaders":["*"]}' \
    --region $AWS_REGION || echo "Function URL may already exist"

PRESCRIPTION_FUNCTION_URL=$(aws lambda get-function-url-config --function-name process-prescription --region $AWS_REGION --query 'FunctionUrl' --output text)

cd ..

# Save function URLs to config
echo "" >> config.env
echo "# Lambda Function URLs" >> config.env
echo "SHELF_ANALYSIS_URL=$SHELF_FUNCTION_URL" >> config.env
echo "PRESCRIPTION_PROCESSING_URL=$PRESCRIPTION_FUNCTION_URL" >> config.env

echo ""
echo "======================================"
echo "✅ Lambda Functions Deployed!"
echo "======================================"
echo ""
echo "Function URLs:"
echo "  Shelf Analysis: $SHELF_FUNCTION_URL"
echo "  Prescription Processing: $PRESCRIPTION_FUNCTION_URL"
echo ""
echo "Updated config.env with function URLs"
echo ""
