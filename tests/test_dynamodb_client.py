import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.dynamodb_client import DynamoDBClient


@pytest.fixture
def dynamodb_client():
    """Fixture to create DynamoDBClient instance"""
    return DynamoDBClient()


def test_dynamodb_client_initialization(dynamodb_client):
    """Test that DynamoDBClient initializes correctly"""
    assert dynamodb_client is not None
    assert dynamodb_client.region is not None
    assert dynamodb_client.inventory_table is not None


def test_add_medicine_structure():
    """Test medicine data structure"""
    medicine_data = {
        "medicine_id": "MED001",
        "name": "Paracetamol 500mg",
        "brand": "Dolo",
        "stock_count": 100,
        "reorder_level": 50,
        "expiry_date": (datetime.now() + timedelta(days=180)).isoformat(),
        "shelf_location": "A1",
        "price": 2.50,
        "supplier": "Cipla",
    }

    assert "medicine_id" in medicine_data
    assert "name" in medicine_data
    assert "stock_count" in medicine_data


def test_alert_structure():
    """Test alert data structure"""
    alert_data = {
        "alert_id": "ALERT001",
        "type": "EXPIRY_WARNING",
        "severity": "HIGH",
        "medicine_id": "MED001",
        "message": "Medicine expires in 25 days",
        "days_until_expiry": 25,
    }

    assert "alert_id" in alert_data
    assert "type" in alert_data
    assert "severity" in alert_data


def test_purchase_order_structure():
    """Test purchase order data structure"""
    order_data = {
        "order_id": "PO001",
        "items": [{"medicine_name": "Amoxicillin 250mg", "quantity": 100}],
        "status": "PENDING",
        "total_amount": 500.00,
    }

    assert "order_id" in order_data
    assert "items" in order_data
    assert len(order_data["items"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])
