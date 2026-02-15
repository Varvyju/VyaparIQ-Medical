# VyaparIQ Medical - Lambda Deployment (FIXED)

Write-Host "Deploying Lambda Functions..." -ForegroundColor Green

# Load configuration
if (-not (Test-Path config.env)) {
    Write-Host "ERROR: config.env not found!" -ForegroundColor Red
    exit 1
}

Get-Content config.env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        Set-Variable -Name $matches[1] -Value $matches[2]
    }
}

$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$ROLE_ARN = "arn:aws:iam::${ACCOUNT_ID}:role/${LAMBDA_ROLE}"

Write-Host "Using Role: $ROLE_ARN" -ForegroundColor Cyan
Write-Host "Region: $AWS_REGION" -ForegroundColor Cyan
Write-Host ""
Write-Host "Waiting 10 seconds for IAM role to propagate..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

cd lambda_functions

# === FUNCTION 1: analyze-shelf-image ===
Write-Host ""
Write-Host "Packaging analyze-shelf-image..." -ForegroundColor Yellow

if (Test-Path package) { Remove-Item -Recurse -Force package }
if (Test-Path analyze_shelf_image.zip) { Remove-Item analyze_shelf_image.zip }

New-Item -ItemType Directory -Path package | Out-Null
pip install -r requirements.txt -t package --quiet --disable-pip-version-check 2>&1 | Out-Null
Copy-Item analyze_shelf_image.py package\

cd package
Compress-Archive -Path * -DestinationPath ..\analyze_shelf_image.zip -Force
cd ..
Remove-Item -Recurse -Force package

Write-Host "Deploying analyze-shelf-image..." -ForegroundColor Cyan

# Try to create (if it doesn't exist)
$output = aws lambda create-function `
    --function-name analyze-shelf-image `
    --runtime python3.12 `
    --role $ROLE_ARN `
    --handler analyze_shelf_image.lambda_handler `
    --zip-file fileb://analyze_shelf_image.zip `
    --timeout 60 `
    --memory-size 512 `
    --environment "Variables={INVENTORY_TABLE=$INVENTORY_TABLE,ALERTS_TABLE=$ALERTS_TABLE}" `
    --region $AWS_REGION 2>&1

if ($LASTEXITCODE -ne 0) {
    # If create failed, check if it's because function exists
    if ($output -like "*ResourceConflictException*" -or $output -like "*already exists*") {
        Write-Host "Function exists, updating..." -ForegroundColor Yellow
        aws lambda update-function-code `
            --function-name analyze-shelf-image `
            --zip-file fileb://analyze_shelf_image.zip `
            --region $AWS_REGION | Out-Null
    } else {
        Write-Host "ERROR creating function:" -ForegroundColor Red
        Write-Host $output -ForegroundColor Red
        Write-Host ""
        Write-Host "Possible causes:" -ForegroundColor Yellow
        Write-Host "1. IAM role not ready (wait 30 more seconds)" -ForegroundColor Yellow
        Write-Host "2. Missing permissions" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Retrying in 30 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
        
        $output = aws lambda create-function `
            --function-name analyze-shelf-image `
            --runtime python3.12 `
            --role $ROLE_ARN `
            --handler analyze_shelf_image.lambda_handler `
            --zip-file fileb://analyze_shelf_image.zip `
            --timeout 60 `
            --memory-size 512 `
            --environment "Variables={INVENTORY_TABLE=$INVENTORY_TABLE,ALERTS_TABLE=$ALERTS_TABLE}" `
            --region $AWS_REGION 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAILED after retry:" -ForegroundColor Red
            Write-Host $output -ForegroundColor Red
            cd ..
            exit 1
        }
    }
} else {
    Write-Host "SUCCESS - Function created!" -ForegroundColor Green
}

# Create Function URL
Write-Host "Creating public Function URL..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

aws lambda add-permission `
    --function-name analyze-shelf-image `
    --statement-id FunctionURLAllowPublicAccess `
    --action lambda:InvokeFunctionUrl `
    --principal "*" `
    --function-url-auth-type NONE `
    --region $AWS_REGION 2>$null

aws lambda create-function-url-config `
    --function-name analyze-shelf-image `
    --auth-type NONE `
    --cors "AllowOrigins=*,AllowMethods=POST,AllowHeaders=*" `
    --region $AWS_REGION 2>$null

Start-Sleep -Seconds 2

$SHELF_URL = (aws lambda get-function-url-config `
    --function-name analyze-shelf-image `
    --region $AWS_REGION `
    --query 'FunctionUrl' `
    --output text)

Write-Host "SUCCESS - URL: $SHELF_URL" -ForegroundColor Green

# === FUNCTION 2: process-prescription ===
Write-Host ""
Write-Host "Packaging process-prescription..." -ForegroundColor Yellow

if (Test-Path package) { Remove-Item -Recurse -Force package }
if (Test-Path process_prescription.zip) { Remove-Item process_prescription.zip }

New-Item -ItemType Directory -Path package | Out-Null
pip install -r requirements.txt -t package --quiet --disable-pip-version-check 2>&1 | Out-Null
Copy-Item process_prescription.py package\

cd package
Compress-Archive -Path * -DestinationPath ..\process_prescription.zip -Force
cd ..
Remove-Item -Recurse -Force package

Write-Host "Deploying process-prescription..." -ForegroundColor Cyan

$output2 = aws lambda create-function `
    --function-name process-prescription `
    --runtime python3.12 `
    --role $ROLE_ARN `
    --handler process_prescription.lambda_handler `
    --zip-file fileb://process_prescription.zip `
    --timeout 60 `
    --memory-size 512 `
    --environment "Variables={PURCHASE_ORDERS_TABLE=$PURCHASE_ORDERS_TABLE,ALERTS_TABLE=$ALERTS_TABLE}" `
    --region $AWS_REGION 2>&1

if ($LASTEXITCODE -ne 0) {
    if ($output2 -like "*ResourceConflictException*" -or $output2 -like "*already exists*") {
        Write-Host "Function exists, updating..." -ForegroundColor Yellow
        aws lambda update-function-code `
            --function-name process-prescription `
            --zip-file fileb://process_prescription.zip `
            --region $AWS_REGION | Out-Null
    } else {
        Write-Host "ERROR: $output2" -ForegroundColor Red
    }
} else {
    Write-Host "SUCCESS - Function created!" -ForegroundColor Green
}

Write-Host "Creating public Function URL..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

aws lambda add-permission `
    --function-name process-prescription `
    --statement-id FunctionURLAllowPublicAccess `
    --action lambda:InvokeFunctionUrl `
    --principal "*" `
    --function-url-auth-type NONE `
    --region $AWS_REGION 2>$null

aws lambda create-function-url-config `
    --function-name process-prescription `
    --auth-type NONE `
    --cors "AllowOrigins=*,AllowMethods=POST,AllowHeaders=*" `
    --region $AWS_REGION 2>$null

Start-Sleep -Seconds 2

$PRESCRIPTION_URL = (aws lambda get-function-url-config `
    --function-name process-prescription `
    --region $AWS_REGION `
    --query 'FunctionUrl' `
    --output text)

Write-Host "SUCCESS - URL: $PRESCRIPTION_URL" -ForegroundColor Green

cd ..

# Save URLs
if ($SHELF_URL) {
    Add-Content config.env "`nSHELF_ANALYSIS_URL=$SHELF_URL"
}
if ($PRESCRIPTION_URL) {
    Add-Content config.env "PRESCRIPTION_PROCESSING_URL=$PRESCRIPTION_URL"
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Magenta
Write-Host "Lambda Deployment Complete!" -ForegroundColor Magenta
Write-Host "======================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Function URLs:" -ForegroundColor Cyan
Write-Host "  Shelf Analysis: $SHELF_URL" -ForegroundColor White
Write-Host "  Prescription: $PRESCRIPTION_URL" -ForegroundColor White
Write-Host ""
Write-Host "Next: cd data && python generate_synthetic_data.py" -ForegroundColor Yellow
Write-Host ""