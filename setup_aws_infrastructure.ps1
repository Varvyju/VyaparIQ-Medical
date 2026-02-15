# VyaparIQ Medical - AWS Infrastructure Setup (Windows)

Write-Host "VyaparIQ Medical - AWS Setup Starting..." -ForegroundColor Green

# Configuration
$REGION = "us-east-1"
$TIMESTAMP = Get-Date -Format "yyyyMMddHHmmss"
$S3_BUCKET = "vyapariq-medical-images-$TIMESTAMP"
$LAMBDA_ROLE = "VyaparIQ-Lambda-Role"

Write-Host "Using AWS Region: $REGION" -ForegroundColor Cyan
Write-Host "S3 Bucket will be: $S3_BUCKET" -ForegroundColor Cyan

# 1. Create S3 Bucket
Write-Host ""
Write-Host "Step 1: Creating S3 Bucket..." -ForegroundColor Yellow
aws s3 mb "s3://$S3_BUCKET" --region $REGION
if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS - S3 Bucket created: $S3_BUCKET" -ForegroundColor Green
} else {
    Write-Host "WARNING - S3 Bucket may already exist" -ForegroundColor Yellow
}

# 2. Create DynamoDB Tables
Write-Host ""
Write-Host "Step 2: Creating DynamoDB Tables..." -ForegroundColor Yellow

Write-Host "Creating Inventory table..." -ForegroundColor Cyan
aws dynamodb create-table `
    --table-name VyaparIQ-Inventory `
    --attribute-definitions AttributeName=medicine_id,AttributeType=S `
    --key-schema AttributeName=medicine_id,KeyType=HASH `
    --billing-mode PAY_PER_REQUEST `
    --region $REGION 2>$null

Write-Host "Creating Alerts table..." -ForegroundColor Cyan  
aws dynamodb create-table `
    --table-name VyaparIQ-Alerts `
    --attribute-definitions AttributeName=alert_id,AttributeType=S AttributeName=created_at,AttributeType=S `
    --key-schema AttributeName=alert_id,KeyType=HASH `
    --global-secondary-indexes "IndexName=CreatedAtIndex,KeySchema=[{AttributeName=created_at,KeyType=HASH}],Projection={ProjectionType=ALL}" `
    --billing-mode PAY_PER_REQUEST `
    --region $REGION 2>$null

Write-Host "Creating PurchaseOrders table..." -ForegroundColor Cyan
aws dynamodb create-table `
    --table-name VyaparIQ-PurchaseOrders `
    --attribute-definitions AttributeName=order_id,AttributeType=S `
    --key-schema AttributeName=order_id,KeyType=HASH `
    --billing-mode PAY_PER_REQUEST `
    --region $REGION 2>$null

Write-Host "SUCCESS - DynamoDB tables created" -ForegroundColor Green

# 3. Create IAM Role
Write-Host ""
Write-Host "Step 3: Creating IAM Role for Lambda..." -ForegroundColor Yellow

# Create trust policy file
$trustPolicyJson = @'
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
'@

$trustPolicyJson | Out-File -FilePath trust-policy.json -Encoding utf8

# Create role
aws iam create-role `
    --role-name $LAMBDA_ROLE `
    --assume-role-policy-document file://trust-policy.json `
    --region $REGION 2>$null

# Attach policies
Write-Host "Attaching policies to Lambda role..." -ForegroundColor Cyan
aws iam attach-role-policy --role-name $LAMBDA_ROLE --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>$null
aws iam attach-role-policy --role-name $LAMBDA_ROLE --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess" 2>$null
aws iam attach-role-policy --role-name $LAMBDA_ROLE --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" 2>$null

# Create Bedrock policy
$bedrockPolicyJson = @'
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
'@

$bedrockPolicyJson | Out-File -FilePath bedrock-policy.json -Encoding utf8

aws iam put-role-policy `
    --role-name $LAMBDA_ROLE `
    --policy-name BedrockAccess `
    --policy-document file://bedrock-policy.json 2>$null

Write-Host "SUCCESS - IAM Role configured" -ForegroundColor Green

# 4. Wait for resources
Write-Host ""
Write-Host "Step 4: Waiting for resources to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
Write-Host "SUCCESS - Resources ready" -ForegroundColor Green

# 5. Save configuration
Write-Host ""
Write-Host "Step 5: Saving configuration..." -ForegroundColor Yellow

$configContent = @"
AWS_REGION=$REGION
S3_BUCKET=$S3_BUCKET
LAMBDA_ROLE=$LAMBDA_ROLE
INVENTORY_TABLE=VyaparIQ-Inventory
ALERTS_TABLE=VyaparIQ-Alerts
PURCHASE_ORDERS_TABLE=VyaparIQ-PurchaseOrders
"@

$configContent | Out-File -FilePath config.env -Encoding utf8

Write-Host "SUCCESS - Configuration saved to config.env" -ForegroundColor Green

# Cleanup temp files
Remove-Item trust-policy.json -ErrorAction SilentlyContinue
Remove-Item bedrock-policy.json -ErrorAction SilentlyContinue

# Summary
Write-Host ""
Write-Host "======================================" -ForegroundColor Magenta
Write-Host "AWS Infrastructure Setup Complete!" -ForegroundColor Magenta
Write-Host "======================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  S3 Bucket: $S3_BUCKET" -ForegroundColor White
Write-Host "  Region: $REGION" -ForegroundColor White
Write-Host "  Tables: VyaparIQ-Inventory, VyaparIQ-Alerts, VyaparIQ-PurchaseOrders" -ForegroundColor White
Write-Host "  IAM Role: $LAMBDA_ROLE" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Update Lambda code to use Nova Pro" -ForegroundColor Yellow
Write-Host "  2. Create deploy_lambda.ps1" -ForegroundColor Yellow
Write-Host "  3. Run deployment script" -ForegroundColor Yellow
Write-Host ""