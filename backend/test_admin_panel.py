import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db, Base, Machine, Quotation, Option
import tempfile
import os
import json
import jwt
from datetime import datetime, timedelta

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_admin.db"
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

# Test data
test_admin_credentials = {
    "username": "admin",
    "password": "ar2810AR"
}

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

@pytest.fixture
def admin_token():
    """Obtener token de admin para tests"""
    response = client.post("/admin/login", json=test_admin_credentials)
    assert response.status_code == 200
    return response.json()["access_token"]

def test_admin_login_success():
    """Test login exitoso de admin"""
    response = client.post("/admin/login", json=test_admin_credentials)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900  # 15 minutos

def test_admin_login_failure():
    """Test login fallido de admin"""
    response = client.post("/admin/login", json={
        "username": "admin",
        "password": "wrong_password"
    })
    assert response.status_code == 401

def test_admin_verify_token(admin_token):
    """Test verificación de token de admin"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/admin/verify", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == True
    assert data["user"] == "admin"

def test_admin_verify_invalid_token():
    """Test verificación de token inválido"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/admin/verify", headers=headers)
    assert response.status_code == 401

def test_get_machines_admin(admin_token, setup_test_data):
    """Test obtener máquinas con autenticación admin"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/admin/machines", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "machines" in data
    assert "total" in data
    assert len(data["machines"]) >= 1

def test_get_machines_admin_with_filters(admin_token, setup_test_data):
    """Test obtener máquinas con filtros"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/admin/machines?active=true&category=Test Category", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["machines"]) >= 1

def test_get_machine_admin(admin_token, setup_test_data):
    """Test obtener una máquina específica"""
    test_data = setup_test_data
    machine = test_data["machine"]
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"/admin/machines/{machine.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == machine.code
    assert data["name"] == machine.name
    assert "options" in data

def test_create_machine_admin(admin_token):
    """Test crear una nueva máquina"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    machine_data = {
        "code": "NEW001",
        "name": "New Test Machine",
        "price": 20000.0,
        "category": "New Category",
        "description": "New test machine",
        "option_ids": []
    }
    
    response = client.post("/admin/machines", json=machine_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "NEW001"
    assert data["name"] == "New Test Machine"

def test_create_machine_duplicate_code(admin_token, setup_test_data):
    """Test crear máquina con código duplicado"""
    test_data = setup_test_data
    machine = test_data["machine"]
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    machine_data = {
        "code": machine.code,  # Código duplicado
        "name": "Another Machine",
        "price": 20000.0,
        "category": "Test Category",
        "description": "Another test machine",
        "option_ids": []
    }
    
    response = client.post("/admin/machines", json=machine_data, headers=headers)
    assert response.status_code == 400

def test_update_machine_admin(admin_token, setup_test_data):
    """Test actualizar una máquina"""
    test_data = setup_test_data
    machine = test_data["machine"]
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    update_data = {
        "name": "Updated Machine Name",
        "price": 25000.0
    }
    
    response = client.put(f"/admin/machines/{machine.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Machine Name"
    assert data["price"] == 25000.0

def test_update_machine_with_options(admin_token, setup_test_data):
    """Test actualizar máquina con opcionales"""
    test_data = setup_test_data
    machine = test_data["machine"]
    option1 = test_data["option1"]
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    update_data = {
        "option_ids": [option1.id]
    }
    
    response = client.put(f"/admin/machines/{machine.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    
    # Verificar que la máquina tiene el opcional asignado
    response = client.get(f"/admin/machines/{machine.id}", headers=headers)
    data = response.json()
    assert len(data["options"]) == 1
    assert data["options"][0]["id"] == option1.id

def test_deactivate_machine_admin(admin_token, setup_test_data):
    """Test desactivar una máquina"""
    test_data = setup_test_data
    machine = test_data["machine"]
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.delete(f"/admin/machines/{machine.id}", headers=headers)
    assert response.status_code == 200
    
    # Verificar que la máquina está desactivada
    response = client.get(f"/admin/machines/{machine.id}", headers=headers)
    data = response.json()
    assert data["active"] == False

def test_unauthorized_access():
    """Test acceso no autorizado a endpoints admin"""
    response = client.get("/admin/machines")
    assert response.status_code == 401

def test_create_machine_with_options(admin_token, setup_test_data):
    """Test crear máquina con opcionales"""
    test_data = setup_test_data
    option1 = test_data["option1"]
    option2 = test_data["option2"]
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    machine_data = {
        "code": "OPT001",
        "name": "Machine with Options",
        "price": 30000.0,
        "category": "Options Category",
        "description": "Machine with options",
        "option_ids": [option1.id, option2.id]
    }
    
    response = client.post("/admin/machines", json=machine_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "OPT001"
    
    # Verificar que tiene los opcionales asignados
    response = client.get(f"/admin/machines/{data['id']}", headers=headers)
    machine_data = response.json()
    assert len(machine_data["options"]) == 2

def test_pagination(admin_token, setup_test_data):
    """Test paginación en listado de máquinas"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/admin/machines?skip=0&limit=5", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert len(data["machines"]) <= 5

# Cleanup test database after all tests
def teardown_module():
    if os.path.exists("test_admin.db"):
        try:
            os.unlink("test_admin.db")
        except:
            pass  # File might be in use 