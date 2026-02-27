import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db, Base, Machine, Quotation, Option
import tempfile
import os
import json

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_options.db"
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
    db.query(Option).delete()
    
    # Add test machine
    test_machine = Machine(
        code="TEST001",
        name="Test Machine",
        price=15000.0,
        category="Test Category",
        description="Test machine description",
        active=True
    )
    db.add(test_machine)
    
    # Add test options
    test_option1 = Option(
        name="Test Option 1",
        price=1000.0,
        description="Test option description 1",
        active=True
    )
    test_option2 = Option(
        name="Test Option 2",
        price=2000.0,
        description="Test option description 2",
        active=True
    )
    db.add(test_option1)
    db.add(test_option2)
    db.commit()
    
    yield {
        "machine": test_machine,
        "option1": test_option1,
        "option2": test_option2
    }
    
    # Cleanup
    db.query(Machine).delete()
    db.query(Quotation).delete()
    db.query(Option).delete()
    db.commit()
    db.close()

def test_get_options(setup_test_data):
    response = client.get("/options")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(option["name"] == "Test Option 1" for option in data)
    assert any(option["name"] == "Test Option 2" for option in data)

def test_create_option():
    option_data = {
        "name": "New Test Option",
        "price": 1500.0,
        "description": "New test option description"
    }
    
    # This should fail without admin credentials
    response = client.post("/admin/options", json=option_data)
    assert response.status_code == 401

def test_update_machine_options(setup_test_data):
    test_data = setup_test_data
    machine = test_data["machine"]
    option1 = test_data["option1"]
    
    # This should fail without admin credentials
    response = client.put(f"/admin/machines/{machine.code}/options", json=[option1.id])
    assert response.status_code == 401

def test_get_machine_options(setup_test_data):
    test_data = setup_test_data
    machine = test_data["machine"]
    
    response = client.get(f"/machines/{machine.code}/options")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_generate_quote_with_options(setup_test_data):
    test_data = setup_test_data
    machine = test_data["machine"]
    option1 = test_data["option1"]
    
    quote_data = {
        "machineCode": machine.code,
        "clientCuit": "20-12345678-9",
        "clientName": "Test Client",
        "clientPhone": "1234567890",
        "option_ids": [option1.id],
        "options_by_machine": {
            machine.code: [option1.id]
        }
    }
    
    response = client.post("/generate-quote", json=quote_data)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

def test_generate_quote_without_options(setup_test_data):
    test_data = setup_test_data
    machine = test_data["machine"]
    
    quote_data = {
        "machineCode": machine.code,
        "clientCuit": "20-12345678-9",
        "clientName": "Test Client",
        "clientPhone": "1234567890"
    }
    
    response = client.post("/generate-quote", json=quote_data)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

def test_option_not_found():
    response = client.get("/machines/TEST001/options")
    assert response.status_code == 404

# Cleanup test database after all tests
def teardown_module():
    if os.path.exists("test_options.db"):
        os.unlink("test_options.db") 