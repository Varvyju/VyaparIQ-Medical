# 🔧 TROUBLESHOOTING GUIDE
## VyaparIQ Medical Edition

---

## 🚨 CRITICAL ISSUES

### Issue 1: Bedrock Access Denied

**Error**: `AccessDeniedException: Could not resolve the foundation model`

**Solutions**:
```bash
# 1. Check if model is enabled
aws bedrock list-foundation-models --region us-east-1

# 2. Enable model access
# Go to AWS Console → Bedrock → Model Access
# Enable: Claude 3.5 Sonnet v2

# 3. Wait 5-10 minutes for approval

# 4. Verify
aws bedrock invoke-model \
  --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":[{"type":"text","text":"test"}]}]}' \
  --region us-east-1 \
  output.json
```

### Issue 2: Lambda Function Timeout

**Error**: `Task timed out after 3.00 seconds`

**Solutions**:
```bash
# Increase timeout to 60 seconds
aws lambda update-function-configuration \
  --function-name analyze-shelf-image \
  --timeout 60

aws lambda update-function-configuration \
  --function-name process-prescription \
  --timeout 60
```

### Issue 3: DynamoDB Table Not Found

**Error**: `ResourceNotFoundException: Cannot do operations on a non-existent table`

**Solutions**:
```bash
# 1. List tables
aws dynamodb list-tables --region us-east-1

# 2. If missing, recreate
./setup_aws_infrastructure.sh

# 3. Wait for tables to become active
aws dynamodb wait table-exists --table-name VyaparIQ-Inventory
```

---

## ⚙️ CONFIGURATION ISSUES

### Issue 4: AWS Credentials Not Working

**Error**: `Unable to locate credentials`

**Solutions**:
```bash
# 1. Check credentials file
cat ~/.aws/credentials

# 2. Reconfigure
aws configure
# Enter: Access Key ID
# Enter: Secret Access Key  
# Enter: us-east-1
# Enter: json

# 3. Test
aws sts get-caller-identity

# 4. Alternative: Use .env file
echo "AWS_ACCESS_KEY_ID=your_key" > .env
echo "AWS_SECRET_ACCESS_KEY=your_secret" >> .env
```

### Issue 5: S3 Bucket Already Exists

**Error**: `BucketAlreadyExists: The requested bucket name is not available`

**Solutions**:
```bash
# S3 bucket names must be globally unique
# Edit setup_aws_infrastructure.sh and change bucket name:

S3_BUCKET="vyapariq-medical-images-YOUR_INITIALS-$(date +%s)"

# Then rerun
./setup_aws_infrastructure.sh
```

---

## 🐍 PYTHON ISSUES

### Issue 6: Module Not Found

**Error**: `ModuleNotFoundError: No module named 'boto3'`

**Solutions**:
```bash
# 1. Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Reinstall dependencies
pip install --upgrade pip
pip install boto3 streamlit Pillow python-dotenv pandas

# 3. Verify
python -c "import boto3; print(boto3.__version__)"
```

### Issue 7: Streamlit Not Running

**Error**: `streamlit: command not found`

**Solutions**:
```bash
# 1. Ensure venv is activated
source venv/bin/activate

# 2. Install streamlit
pip install streamlit

# 3. Run with full path
python -m streamlit run frontend/app.py

# 4. Check version
streamlit --version
```

---

## 🔌 LAMBDA DEPLOYMENT ISSUES

### Issue 8: Lambda Role Doesn't Exist

**Error**: `InvalidParameterValueException: The role defined for the function cannot be assumed by Lambda`

**Solutions**:
```bash
# 1. Wait 10 seconds after role creation (IAM propagation)
sleep 10

# 2. Verify role exists
aws iam get-role --role-name VyaparIQ-Lambda-Role

# 3. Recreate role
aws iam create-role \
  --role-name VyaparIQ-Lambda-Role \
  --assume-role-policy-document file://lambda-trust-policy.json
```

### Issue 9: Lambda Package Too Large

**Error**: `InvalidParameterValueException: Unzipped size must be smaller than 262144000 bytes`

**Solutions**:
```bash
# Lambda has been deployed correctly with optimized dependencies
# If you modify and add heavy libraries:

# 1. Use Lambda Layers
# 2. Remove unnecessary packages from requirements.txt
# 3. Use --no-deps flag for specific packages

# For this project, size should be ~15 MB (well under limit)
```

---

## 🖼️ IMAGE PROCESSING ISSUES

### Issue 10: Image Upload Fails in Streamlit

**Error**: `PIL.UnidentifiedImageError: cannot identify image file`

**Solutions**:
```python
# Ensure image is valid format
from PIL import Image
import io

try:
    image = Image.open(uploaded_file)
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
except Exception as e:
    st.error(f"Invalid image format: {e}")
```

### Issue 11: Base64 Encoding Issues

**Error**: `Invalid base64 string`

**Solutions**:
```python
import base64
import io

# Correct encoding
img_byte_arr = io.BytesIO()
image.save(img_byte_arr, format='JPEG')
img_byte_arr.seek(0)
image_base64 = base64.b64encode(img_byte_arr.read()).decode('utf-8')

# Remove data URI prefix if present
if image_base64.startswith('data:'):
    image_base64 = image_base64.split(',')[1]
```

---

## 🗄️ DYNAMODB ISSUES

### Issue 12: Item Not Found

**Error**: `botocore.exceptions.ClientError: An error occurred (ResourceNotFoundException)`

**Solutions**:
```python
# Always use try-except for get_item
try:
    response = table.get_item(Key={'medicine_id': 'some_id'})
    item = response.get('Item')
    if not item:
        print("Item not found")
except Exception as e:
    print(f"Error: {e}")

# Use scan for queries without exact key
response = table.scan(
    FilterExpression='medicine_name = :name',
    ExpressionAttributeValues={':name': 'Paracetamol'}
)
```

### Issue 13: DynamoDB Write Throttling

**Error**: `ProvisionedThroughputExceededException: Rate exceeded`

**Solutions**:
```bash
# We use PAY_PER_REQUEST (on-demand) billing, so this shouldn't happen
# But if it does:

aws dynamodb update-table \
  --table-name VyaparIQ-Inventory \
  --billing-mode PAY_PER_REQUEST
```

---

## 🤖 BEDROCK API ISSUES

### Issue 14: JSON Parsing Error from Bedrock

**Error**: `JSONDecodeError: Expecting value`

**Solutions**:
```python
# Bedrock sometimes returns markdown-wrapped JSON
import json
import re

def clean_bedrock_response(response_text):
    # Remove markdown code fences
    if '```json' in response_text:
        response_text = response_text.split('```json')[1].split('```')[0]
    elif '```' in response_text:
        response_text = response_text.split('```')[1].split('```')[0]
    
    # Remove any leading/trailing whitespace
    response_text = response_text.strip()
    
    # Parse JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        # Log the raw response for debugging
        print(f"Failed to parse: {response_text[:200]}")
        raise e

# Use in Lambda function
ai_response = response_body['content'][0]['text']
result = clean_bedrock_response(ai_response)
```

### Issue 15: Bedrock Rate Limiting

**Error**: `ThrottlingException: Rate exceeded for operation`

**Solutions**:
```python
import time
from botocore.exceptions import ClientError

def call_bedrock_with_retry(bedrock_client, model_id, body, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=body
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 1  # Exponential backoff
                    print(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
            else:
                raise
```

---

## 🌐 STREAMLIT UI ISSUES

### Issue 16: Streamlit Caching Errors

**Error**: `UnhashableTypeError: Cannot hash object of type`

**Solutions**:
```python
# Don't cache boto3 clients/resources with @st.cache_data
# Use @st.cache_resource instead

@st.cache_resource
def get_aws_clients():
    # This creates clients once and reuses them
    return {
        's3': boto3.client('s3'),
        'dynamodb': boto3.resource('dynamodb')
    }

# For data caching, use @st.cache_data
@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_inventory():
    # This caches the returned data
    return list(table.scan()['Items'])
```

### Issue 17: Streamlit App Won't Start

**Error**: `Address already in use`

**Solutions**:
```bash
# 1. Kill existing Streamlit process
pkill -f streamlit

# 2. Use different port
streamlit run app.py --server.port 8502

# 3. Find and kill process on port 8501
lsof -ti:8501 | xargs kill -9
```

---

## 📱 MOBILE/BROWSER ISSUES

### Issue 18: Camera Not Working in Browser

**Solutions**:
- Use HTTPS (required for camera access)
- Or use file upload instead of camera capture
- Test on different browsers (Chrome works best)

### Issue 19: Large Image Upload Fails

**Solutions**:
```python
# Resize images before processing
from PIL import Image

def resize_image(image, max_size=(1024, 1024)):
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image

# In Streamlit
if uploaded_file:
    image = Image.open(uploaded_file)
    image = resize_image(image)
```

---

## 🔍 DEBUGGING TIPS

### Enable Verbose Logging

```python
# In Lambda functions
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

logger.debug(f"Received event: {json.dumps(event)}")
logger.info(f"Processing image: {s3_key}")
logger.error(f"Error occurred: {str(e)}")
```

### Test Lambda Locally

```bash
# Run Lambda function directly
cd lambda_functions
python3 analyze_shelf_image.py

# Or use AWS SAM for local testing
sam local invoke analyze-shelf-image \
  --event test-event.json
```

### Check CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/analyze-shelf-image --follow

# Or in AWS Console:
# CloudWatch → Log Groups → /aws/lambda/analyze-shelf-image
```

---

## 📊 PERFORMANCE ISSUES

### Issue 20: Slow Bedrock Response

**Problem**: API calls taking >10 seconds

**Solutions**:
1. Use Claude 3 Haiku for faster responses (trade accuracy for speed)
2. Reduce max_tokens parameter
3. Simplify prompts
4. Implement response streaming (not available in current Bedrock Python SDK)

```python
# Use faster model
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'

# Reduce tokens
request_body = {
    "max_tokens": 2000,  # Instead of 4000
    # ...
}
```

### Issue 21: DynamoDB Scan Too Slow

**Problem**: Dashboard takes >5 seconds to load

**Solutions**:
```python
# 1. Use pagination
def scan_table_efficiently(table, filter_expr=None):
    items = []
    scan_kwargs = {'Limit': 100}  # Process in batches
    
    if filter_expr:
        scan_kwargs['FilterExpression'] = filter_expr
    
    response = table.scan(**scan_kwargs)
    items.extend(response['Items'])
    
    # Get first 100 items only for dashboard
    return items[:100]

# 2. Add caching
@st.cache_data(ttl=30)  # Cache for 30 seconds
def get_dashboard_data():
    return scan_table_efficiently(inventory_table)
```

---

## 🚀 DEPLOYMENT ISSUES

### Issue 22: Function URL Not Working

**Error**: `403 Forbidden` when accessing function URL

**Solutions**:
```bash
# 1. Check CORS configuration
aws lambda get-function-url-config \
  --function-name analyze-shelf-image

# 2. Update CORS if needed
aws lambda update-function-url-config \
  --function-name analyze-shelf-image \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["POST","GET"],"AllowHeaders":["*"]}'

# 3. Verify auth type is NONE
aws lambda update-function-url-config \
  --function-name analyze-shelf-image \
  --auth-type NONE
```

---

## 🆘 WHEN ALL ELSE FAILS

### Nuclear Option: Full Reset

```bash
# ⚠️ WARNING: This deletes everything

# 1. Delete Lambda functions
aws lambda delete-function --function-name analyze-shelf-image
aws lambda delete-function --function-name process-prescription

# 2. Delete DynamoDB tables
aws dynamodb delete-table --table-name VyaparIQ-Inventory
aws dynamodb delete-table --table-name VyaparIQ-Alerts
aws dynamodb delete-table --table-name VyaparIQ-PurchaseOrders

# 3. Delete S3 bucket (after emptying)
aws s3 rb s3://YOUR-BUCKET-NAME --force

# 4. Delete IAM role
aws iam delete-role --role-name VyaparIQ-Lambda-Role

# 5. Wait 1 minute

# 6. Rerun setup
./setup_aws_infrastructure.sh
./deploy_lambda.sh
```

---

## 📞 GETTING HELP

### Resources
1. **AWS Documentation**: https://docs.aws.amazon.com/
2. **Bedrock API Reference**: https://docs.aws.amazon.com/bedrock/
3. **Streamlit Docs**: https://docs.streamlit.io/
4. **Claude API Docs**: https://docs.anthropic.com/

### Common Search Queries
- "AWS Bedrock Claude 3.5 Sonnet examples"
- "Lambda DynamoDB Python boto3"
- "Streamlit image upload tutorial"
- "Bedrock vision API multimodal"

### Ask for Help
- AWS Forums: https://repost.aws/
- Stack Overflow: Tag `aws-lambda` `amazon-bedrock`
- Anthropic Discord: https://discord.gg/anthropic

---

## ✅ HEALTH CHECK SCRIPT

```bash
#!/bin/bash
# Run this to verify everything is working

echo "=== VyaparIQ Medical Health Check ==="

# Check AWS credentials
echo "1. Checking AWS credentials..."
aws sts get-caller-identity && echo "✅ AWS credentials OK" || echo "❌ AWS credentials FAILED"

# Check Bedrock model access
echo "
2. Checking Bedrock model access..."
aws bedrock list-foundation-models --region us-east-1 | grep -q "claude-3-5-sonnet" && echo "✅ Bedrock access OK" || echo "❌ Bedrock access FAILED"

# Check DynamoDB tables
echo "
3. Checking DynamoDB tables..."
aws dynamodb describe-table --table-name VyaparIQ-Inventory > /dev/null 2>&1 && echo "✅ Inventory table OK" || echo "❌ Inventory table FAILED"

# Check Lambda functions
echo "
4. Checking Lambda functions..."
aws lambda get-function --function-name analyze-shelf-image > /dev/null 2>&1 && echo "✅ analyze-shelf-image OK" || echo "❌ analyze-shelf-image FAILED"

# Check S3 bucket
echo "
5. Checking S3 bucket..."
source config.env
aws s3 ls s3://$S3_BUCKET > /dev/null 2>&1 && echo "✅ S3 bucket OK" || echo "❌ S3 bucket FAILED"

echo "
=== Health Check Complete ==="
```

Save as `health_check.sh` and run: `chmod +x health_check.sh && ./health_check.sh`

---

**Remember**: 90% of issues are solved by:
1. Reading error messages carefully
2. Checking AWS Console
3. Verifying IAM permissions
4. Waiting for AWS resource propagation (60 seconds)

**Good luck! 🚀**
