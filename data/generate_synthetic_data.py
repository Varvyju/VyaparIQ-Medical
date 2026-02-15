#!/usr/bin/env python3
"""
Generate synthetic test data for VyaparIQ Medical demo
"""

import boto3
from datetime import datetime, timedelta
import random
import json
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Sample Indian medicines
SAMPLE_MEDICINES = [
    {"name": "Paracetamol 500mg", "brand": "Dolo", "form": "tablet"},
    {"name": "Paracetamol 650mg", "brand": "Crocin", "form": "tablet"},
    {"name": "Amoxicillin 250mg", "brand": "Novamox", "form": "capsule"},
    {"name": "Azithromycin 500mg", "brand": "Azithral", "form": "tablet"},
    {"name": "Cetirizine 10mg", "brand": "Cetzine", "form": "tablet"},
    {"name": "Omeprazole 20mg", "brand": "Omez", "form": "capsule"},
    {"name": "Metformin 500mg", "brand": "Glycomet", "form": "tablet"},
    {"name": "Aspirin 75mg", "brand": "Ecosprin", "form": "tablet"},
    {"name": "Amoxicillin + Clavulanic Acid", "brand": "Augmentin", "form": "tablet"},
    {"name": "Diclofenac 50mg", "brand": "Voveran", "form": "tablet"},
    {"name": "Ibuprofen 400mg", "brand": "Brufen", "form": "tablet"},
    {"name": "Ciprofloxacin 500mg", "brand": "Ciplox", "form": "tablet"},
    {"name": "Pantoprazole 40mg", "brand": "Pan", "form": "tablet"},
    {"name": "Montelukast 10mg", "brand": "Montair", "form": "tablet"},
    {"name": "Salbutamol Inhaler", "brand": "Asthalin", "form": "inhaler"},
    {"name": "ORS", "brand": "Electral", "form": "powder"},
    {"name": "Multivitamin", "brand": "Becosules", "form": "capsule"},
    {"name": "Calcium + Vitamin D3", "brand": "Shelcal", "form": "tablet"},
    {"name": "Ranitidine 150mg", "brand": "Aciloc", "form": "tablet"},
    {"name": "Levocetirizine 5mg", "brand": "Levocet", "form": "tablet"}
]

def generate_inventory_data():
    """Generate sample inventory data"""
    inventory_table = dynamodb.Table('VyaparIQ-Inventory')
    
    print("Generating inventory data...")
    
    for medicine in SAMPLE_MEDICINES:
        stock_quantity = random.randint(0, 50)
        
        # Some medicines have expiry dates
        has_expiry = random.choice([True, False, False])  # 1/3 chance
        expiry_date = None
        if has_expiry:
            days_until_expiry = random.randint(10, 180)
            expiry_date = (datetime.now() + timedelta(days=days_until_expiry)).strftime('%Y-%m-%d')
        
        inventory_item = {
            'medicine_id': f"{medicine['name'].lower().replace(' ', '_')}_{medicine['brand']}",
            'medicine_name': medicine['name'],
            'brand': medicine['brand'],
            'stock_quantity': stock_quantity,
            'expiry_date': expiry_date,
            'confidence': Decimal(str(round(random.uniform(0.85, 0.98), 2))),
            'location': random.choice(['top', 'middle', 'bottom']),
            'last_scanned': datetime.now().isoformat(),
            'image_reference': 'synthetic_data/sample_shelf.jpg'
        }
        
        inventory_table.put_item(Item=inventory_item)
        print(f"  Added: {medicine['name']} ({medicine['brand']}) - Stock: {stock_quantity}")
    
    print(f"Generated {len(SAMPLE_MEDICINES)} inventory items")

def generate_alerts():
    """Generate sample alerts"""
    alerts_table = dynamodb.Table('VyaparIQ-Alerts')
    
    print("")
    print("Generating alerts...")
    
    alert_count = 0
    
    # Expiry warnings
    for i in range(3):
        medicine = random.choice(SAMPLE_MEDICINES)
        days_remaining = random.randint(5, 45)
        
        alert = {
            'alert_id': f"expiry_{medicine['name']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}",
            'type': 'expiry_warning',
            'severity': 'high' if days_remaining < 15 else 'medium',
            'medicine_name': medicine['name'],
            'expiry_date': (datetime.now() + timedelta(days=days_remaining)).strftime('%Y-%m-%d'),
            'days_remaining': days_remaining,
            'created_at': datetime.now().isoformat(),
            'resolved': False,
            'message': f"{medicine['name']} ({medicine['brand']}) expires in {days_remaining} days"
        }
        alerts_table.put_item(Item=alert)
        alert_count += 1
        print(f"  Created expiry alert for {medicine['name']}")
    
    # Missing essentials
    missing_medicines = ["Insulin", "Bandages", "Antiseptic Cream"]
    for missing in missing_medicines:
        alert = {
            'alert_id': f"missing_{missing}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'type': 'missing_essential',
            'severity': 'medium',
            'medicine_name': missing,
            'created_at': datetime.now().isoformat(),
            'resolved': False,
            'message': f"Essential medicine {missing} is out of stock"
        }
        alerts_table.put_item(Item=alert)
        alert_count += 1
        print(f"  Created missing alert for {missing}")
    
    # Low stock warning
    alert = {
        'alert_id': f"low_stock_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'type': 'low_stock_warning',
        'severity': 'low',
        'created_at': datetime.now().isoformat(),
        'resolved': False,
        'message': 'Overall shelf stock level is low - consider restocking'
    }
    alerts_table.put_item(Item=alert)
    alert_count += 1
    
    print(f"Generated {alert_count} alerts")

def generate_purchase_orders():
    """Generate sample purchase orders"""
    po_table = dynamodb.Table('VyaparIQ-PurchaseOrders')
    
    print("")
    print("Generating purchase orders...")
    
    for i in range(2):
        order_id = f"PO_{datetime.now().strftime('%Y%m%d%H%M')}_{i}"
        
        # Random medicines for this order
        order_medicines = random.sample(SAMPLE_MEDICINES, random.randint(3, 6))
        
        items = []
        for med in order_medicines:
            items.append({
                'medicine_name': med['name'],
                'quantity': random.randint(10, 50),
                'form': med['form'],
                'dosage': med['name'].split()[-1] if 'mg' in med['name'] else 'standard',
                'estimated_unit_price': random.randint(5, 100),
                'confidence': Decimal(str(round(random.uniform(0.85, 0.95), 2)))
            })
        
        purchase_order = {
            'order_id': order_id,
            'items': items,
            'total_items': len(items),
            'status': random.choice(['pending', 'approved', 'ordered']),
            'created_at': (datetime.now() - timedelta(days=random.randint(0, 7))).isoformat(),
            'prescription_date': (datetime.now() - timedelta(days=random.randint(0, 3))).strftime('%Y-%m-%d'),
            'patient_name': random.choice(['Ramesh Kumar', 'Priya Sharma', 'Amit Patel', 'Sunita Devi']),
            'doctor_name': random.choice(['Dr. Verma', 'Dr. Singh', 'Dr. Gupta']),
            'has_interactions': False,
            'interactions': []
        }
        
        po_table.put_item(Item=purchase_order)
        print(f"  Created purchase order: {order_id}")
    
    print("Generated 2 purchase orders")

def main():
    print("=" * 60)
    print("VyaparIQ Medical - Synthetic Data Generator")
    print("=" * 60)
    
    try:
        generate_inventory_data()
        generate_alerts()
        generate_purchase_orders()
        
        print("")
        print("=" * 60)
        print("All synthetic data generated successfully!")
        print("=" * 60)
        print("")
        print("You can now run the Streamlit app and see the dashboard populated.")
        
    except Exception as e:
        print("")
        print(f"ERROR: {str(e)}")
        print("Make sure your AWS credentials are configured and DynamoDB tables exist.")

if __name__ == "__main__":
    main()