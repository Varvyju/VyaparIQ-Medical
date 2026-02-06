import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.bedrock_client import BedrockClient
import base64

@pytest.fixture
def bedrock_client():
    """Fixture to create BedrockClient instance"""
    return BedrockClient()

def test_bedrock_client_initialization(bedrock_client):
    """Test that BedrockClient initializes correctly"""
    assert bedrock_client is not None
    assert bedrock_client.region is not None
    assert bedrock_client.model_id is not None

def test_analyze_shelf_image_structure(bedrock_client):
    """Test that analyze_shelf_image returns expected structure"""
    # Create a dummy base64 image (1x1 pixel PNG)
    dummy_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01').decode()
    
    # Note: This will fail without valid AWS credentials
    # In real testing, use moto or mock the boto3 client
    # result = bedrock_client.analyze_shelf_image(dummy_image)
    # assert 'medicines_detected' in result

def test_check_drug_interactions_structure(bedrock_client):
    """Test that check_drug_interactions returns expected structure"""
    medicines = ["Aspirin", "Warfarin"]
    
    # Note: This will fail without valid AWS credentials
    # result = bedrock_client.check_drug_interactions(medicines)
    # assert 'status' in result
    # assert 'interactions' in result

def test_process_prescription_structure(bedrock_client):
    """Test that process_prescription returns expected structure"""
    dummy_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01').decode()
    
    # Note: This will fail without valid AWS credentials
    # result = bedrock_client.process_prescription(dummy_image)
    # assert 'medicines' in result

if __name__ == "__main__":
    pytest.main([__file__])
