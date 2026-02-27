import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db, Base, Machine, Quotation
import tempfile
import os

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_enhanced.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def setup_test_data():
    db = TestingSessionLocal()
    # Clear existing data
    db.query(Machine).delete()
    db.query(Quotation).delete()
    
    # Add test machine
    test_machine = Machine(
        code="TEST001",
        name="Test Machine Enhanced",
        price=15000.0,
        category="Test Category",
        description="Test machine description",
        active=True
    )
    db.add(test_machine)
    db.commit()
    
    yield test_machine
    
    # Cleanup
    db.query(Machine).delete()
    db.query(Quotation).delete()
    db.commit()
    db.close()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_get_machines(setup_test_data):
    response = client.get("/machines")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(machine["code"] == "TEST001" for machine in data)

def test_get_machinery_catalog():
    response = client.get("/machines/catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "categoria" in data[0]
    assert "productos" in data[0]

def test_get_machine_by_code(setup_test_data):
    machine = setup_test_data
    response = client.get(f"/machines/{machine.code}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "TEST001"
    assert data["name"] == "Test Machine Enhanced"

def test_update_machine_price(setup_test_data):
    machine = setup_test_data
    response = client.put(f"/machines/{machine.code}", json={"price": 18000.0})
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 18000.0

def test_generate_quote_with_discount(setup_test_data):
    machine = setup_test_data
    quote_data = {
        "machineCode": machine.code,
        "clientCuit": "20-12345678-9",
        "clientName": "Test Client Enhanced",
        "clientPhone": "1234567890",
        "clientEmail": "test@example.com",
        "clientCompany": "Test Company",
        "notes": "Test notes with enhanced features",
        "applyDiscount": True
    }
    
    response = client.post("/generate-quote", json=quote_data)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

def test_generate_quote_without_discount(setup_test_data):
    machine = setup_test_data
    quote_data = {
        "machineCode": machine.code,
        "clientCuit": "20-12345678-9",
        "clientName": "Test Client No Discount",
        "clientPhone": "1234567890",
        "applyDiscount": False
    }
    
    response = client.post("/generate-quote", json=quote_data)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

def test_machine_not_found():
    response = client.get("/machines/NONEXISTENT")
    assert response.status_code == 404

def test_quote_machine_not_found():
    quote_data = {
        "machineCode": "NONEXISTENT",
        "clientCuit": "20-12345678-9",
        "clientName": "Test Client",
        "clientPhone": "1234567890",
        "applyDiscount": False
    }
    
    response = client.post("/generate-quote", json=quote_data)
    assert response.status_code == 404

# Cleanup test database after all tests
def teardown_module():
    if os.path.exists("test_enhanced.db"):
        os.unlink("test_enhanced.db")
