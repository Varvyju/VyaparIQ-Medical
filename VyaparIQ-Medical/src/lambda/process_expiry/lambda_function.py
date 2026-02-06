import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

INVENTORY_TABLE = os.environ.get('DYNAMODB_INVENTORY_TABLE', 'VyaparIQ-Inventory')
ALERTS_TABLE = os.environ.get('DYNAMODB_ALERTS_TABLE', 'VyaparIQ-Alerts')

def lambda_handler(event, context):
    """
    Lambda function to process expiry dates and create alerts
    Scheduled to run daily via EventBridge
    """
    
    try:
        inventory_table = dynamodb.Table(INVENTORY_TABLE)
        alerts_table = dynamodb.Table(ALERTS_TABLE)
        
        # Scan inventory for all medicines
        response = inventory_table.scan()
        medicines = response.get('Items', [])
        
        current_date = datetime.now()
        alerts_created = 0
        
        for medicine in medicines:
            expiry_str = medicine.get('expiry_date', '')
            
            if not expiry_str:
                continue
            
            try:
                # Parse expiry date
                expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                days_until_expiry = (expiry_date - current_date).days
                
                # Determine severity and create alert
                severity = None
                alert_type = 'EXPIRY_WARNING'
                
                if days_until_expiry < 0:
                    severity = 'CRITICAL'
                    message = f"{medicine['name']} has EXPIRED {abs(days_until_expiry)} days ago"
                elif days_until_expiry <= 30:
                    severity = 'HIGH'
                    message = f"{medicine['name']} expires in {days_until_expiry} days - URGENT action needed"
                elif days_until_expiry <= 60:
                    severity = 'MEDIUM'
                    message = f"{medicine['name']} expires in {days_until_expiry} days - Prioritize sales"
                elif days_until_expiry <= 90:
                    severity = 'LOW'
                    message = f"{medicine['name']} expires in {days_until_expiry} days - Monitor stock"
                
                if severity:
                    # Create alert
                    alert_id = f"ALERT_{medicine['medicine_id']}_{current_date.strftime('%Y%m%d')}"
                    
                    alert_item = {
                        'alert_id': alert_id,
                        'type': alert_type,
                        'severity': severity,
                        'medicine_id': medicine['medicine_id'],
                        'message': message,
                        'created_at': current_date.isoformat(),
                        'resolved': False,
                        'days_until_expiry': days_until_expiry,
                        'stock_count': medicine.get('stock_count', 0)
                    }
                    
                    alerts_table.put_item(Item=alert_item)
                    alerts_created += 1
                    
            except Exception as e:
                print(f"Error processing medicine {medicine.get('medicine_id')}: {str(e)}")
                continue
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'medicines_processed': len(medicines),
                'alerts_created': alerts_created,
                'timestamp': current_date.isoformat()
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process expiry dates'
            })
        }
