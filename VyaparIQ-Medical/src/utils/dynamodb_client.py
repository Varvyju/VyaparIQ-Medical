import boto3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal

class DynamoDBClient:
    """Client for interacting with DynamoDB tables"""
    
    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.inventory_table = os.getenv('DYNAMODB_INVENTORY_TABLE', 'VyaparIQ-Inventory')
        self.alerts_table = os.getenv('DYNAMODB_ALERTS_TABLE', 'VyaparIQ-Alerts')
        self.orders_table = os.getenv('DYNAMODB_ORDERS_TABLE', 'VyaparIQ-PurchaseOrders')
        
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        
        self.inventory = self.dynamodb.Table(self.inventory_table)
        self.alerts = self.dynamodb.Table(self.alerts_table)
        self.orders = self.dynamodb.Table(self.orders_table)
    
    def add_medicine(self, medicine_data: Dict) -> bool:
        """Add or update medicine in inventory"""
        try:
            item = {
                'medicine_id': medicine_data['medicine_id'],
                'name': medicine_data['name'],
                'brand': medicine_data.get('brand', ''),
                'stock_count': medicine_data['stock_count'],
                'reorder_level': medicine_data.get('reorder_level', 50),
                'expiry_date': medicine_data.get('expiry_date', ''),
                'last_updated': datetime.now().isoformat(),
                'shelf_location': medicine_data.get('shelf_location', ''),
                'price': Decimal(str(medicine_data.get('price', 0))),
                'supplier': medicine_data.get('supplier', '')
            }
            
            self.inventory.put_item(Item=item)
            return True
            
        except Exception as e:
            print(f"Error adding medicine: {str(e)}")
            return False
    
    def get_medicine(self, medicine_id: str) -> Optional[Dict]:
        """Get medicine details by ID"""
        try:
            response = self.inventory.get_item(Key={'medicine_id': medicine_id})
            return response.get('Item')
        except Exception as e:
            print(f"Error getting medicine: {str(e)}")
            return None
    
    def get_all_medicines(self) -> List[Dict]:
        """Get all medicines in inventory"""
        try:
            response = self.inventory.scan()
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting all medicines: {str(e)}")
            return []
    
    def update_stock(self, medicine_id: str, new_count: int) -> bool:
        """Update stock count for a medicine"""
        try:
            self.inventory.update_item(
                Key={'medicine_id': medicine_id},
                UpdateExpression='SET stock_count = :count, last_updated = :updated',
                ExpressionAttributeValues={
                    ':count': new_count,
                    ':updated': datetime.now().isoformat()
                }
            )
            return True
        except Exception as e:
            print(f"Error updating stock: {str(e)}")
            return False
    
    def get_expiring_medicines(self, days: int = 30) -> List[Dict]:
        """Get medicines expiring within specified days"""
        try:
            all_medicines = self.get_all_medicines()
            expiring = []
            
            cutoff_date = datetime.now() + timedelta(days=days)
            
            for med in all_medicines:
                expiry_str = med.get('expiry_date', '')
                if expiry_str:
                    try:
                        expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                        if expiry_date <= cutoff_date:
                            days_until = (expiry_date - datetime.now()).days
                            med['days_until_expiry'] = max(0, days_until)
                            expiring.append(med)
                    except:
                        continue
            
            # Sort by days until expiry
            expiring.sort(key=lambda x: x['days_until_expiry'])
            return expiring
            
        except Exception as e:
            print(f"Error getting expiring medicines: {str(e)}")
            return []
    
    def create_alert(self, alert_data: Dict) -> bool:
        """Create a new alert"""
        try:
            item = {
                'alert_id': alert_data['alert_id'],
                'type': alert_data['type'],
                'severity': alert_data.get('severity', 'MEDIUM'),
                'medicine_id': alert_data.get('medicine_id', ''),
                'message': alert_data['message'],
                'created_at': datetime.now().isoformat(),
                'resolved': False,
                'days_until_expiry': alert_data.get('days_until_expiry', 0)
            }
            
            self.alerts.put_item(Item=item)
            return True
            
        except Exception as e:
            print(f"Error creating alert: {str(e)}")
            return False
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent unresolved alerts"""
        try:
            response = self.alerts.scan(
                FilterExpression='resolved = :resolved',
                ExpressionAttributeValues={':resolved': False},
                Limit=limit
            )
            
            alerts = response.get('Items', [])
            # Sort by created_at descending
            alerts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return alerts[:limit]
            
        except Exception as e:
            print(f"Error getting alerts: {str(e)}")
            return []
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        try:
            self.alerts.update_item(
                Key={'alert_id': alert_id},
                UpdateExpression='SET resolved = :resolved',
                ExpressionAttributeValues={':resolved': True}
            )
            return True
        except Exception as e:
            print(f"Error resolving alert: {str(e)}")
            return False
    
    def create_purchase_order(self, order_data: Dict) -> bool:
        """Create a new purchase order"""
        try:
            item = {
                'order_id': order_data['order_id'],
                'items': order_data['items'],
                'status': order_data.get('status', 'PENDING'),
                'created_at': datetime.now().isoformat(),
                'total_amount': Decimal(str(order_data.get('total_amount', 0))),
                'supplier': order_data.get('supplier', ''),
                'notes': order_data.get('notes', '')
            }
            
            self.orders.put_item(Item=item)
            return True
            
        except Exception as e:
            print(f"Error creating purchase order: {str(e)}")
            return False
    
    def get_purchase_orders(self, status: Optional[str] = None) -> List[Dict]:
        """Get purchase orders, optionally filtered by status"""
        try:
            if status:
                response = self.orders.scan(
                    FilterExpression='#status = :status',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': status}
                )
            else:
                response = self.orders.scan()
            
            orders = response.get('Items', [])
            # Sort by created_at descending
            orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return orders
            
        except Exception as e:
            print(f"Error getting purchase orders: {str(e)}")
            return []
    
    def get_low_stock_medicines(self) -> List[Dict]:
        """Get medicines below reorder level"""
        try:
            all_medicines = self.get_all_medicines()
            low_stock = [
                med for med in all_medicines 
                if med.get('stock_count', 0) <= med.get('reorder_level', 50)
            ]
            return low_stock
        except Exception as e:
            print(f"Error getting low stock medicines: {str(e)}")
            return []
