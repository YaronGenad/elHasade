import os
import sys
# Set environment variables for testing (conftest.py handles these when running
# via pytest; setdefault ensures they work for direct `python ...` execution too)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_alhasade_complete.db")
os.environ.setdefault("AUTH_RATE_LIMIT", "1000/minute")
os.environ.setdefault("GENERATION_RATE_LIMIT", "1000/minute")

# Remove existing test database file to ensure clean state (before any imports open it)
try:
    if os.path.exists("./test_alhasade_complete.db"):
        os.remove("./test_alhasade_complete.db")
except PermissionError:
    pass  # File locked by another process; will be overwritten by create_all

# Add src to path so we can import the pipeline modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the app and set up the database
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import engine
from app.db.base import Base
from app.models import user, query, material

# Create the tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_register_user():
    response = client.post(
        "/auth/register",
        json={
            "email": "test_register_complete@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test_register_complete@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data
    print("User registration test passed!")

def test_register_duplicate_email():
    # First register a user
    client.post(
        "/auth/register",
        json={
            "email": "test_dup@example.com",
            "password": "testpassword123",
            "full_name": "Test User 1"
        },
    )
    
    # Try to register with same email
    response = client.post(
        "/auth/register",
        json={
            "email": "test_dup@example.com",
            "password": "testpassword123",
            "full_name": "Test User 2"
        },
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]
    print("Duplicate email registration test passed!")

def test_login_user():
    # First register a user
    client.post(
        "/auth/register",
        json={
            "email": "test_login@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        },
    )
    
    # Then login
    response = client.post(
        "/auth/login",
        data={
            "username": "test_login@example.com",
            "password": "testpassword123"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    print("User login test passed!")

def test_login_invalid_credentials():
    # Try to login with non-existent user
    response = client.post(
        "/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "testpassword123"
        },
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
    
    # Try to login with wrong password
    client.post(
        "/auth/register",
        json={
            "email": "test_wrong@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        },
    )
    
    response = client.post(
        "/auth/login",
        data={
            "username": "test_wrong@example.com",
            "password": "wrongpassword"
        },
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
    print("Invalid login credentials test passed!")

def test_refresh_token():
    # First register and login to get tokens
    client.post(
        "/auth/register",
        json={
            "email": "test_refresh@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        },
    )
    
    login_response = client.post(
        "/auth/login",
        data={
            "username": "test_refresh@example.com",
            "password": "testpassword123"
        },
    )
    tokens = login_response.json()
    refresh_token = tokens["refresh_token"]
    
    # Then refresh
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    print("Token refresh test passed!")

def test_refresh_invalid_token():
    # Try to refresh with invalid token
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid.token.here"}
    )
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]
    print("Invalid refresh token test passed!")

def test_get_current_user():
    # First register and login to get token
    client.post(
        "/auth/register",
        json={
            "email": "test_me@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        },
    )
    
    login_response = client.post(
        "/auth/login",
        data={
            "username": "test_me@example.com",
            "password": "testpassword123"
        },
    )
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # Get current user
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test_me@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data  # id is now a UUID
    print("Get current user test passed!")

def test_get_current_user_invalid_token():
    # Try to get current user with invalid token
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.json()["detail"]
    print("Get current user with invalid token test passed!")

if __name__ == "__main__":
    test_register_user()
    test_register_duplicate_email()
    test_login_user()
    test_login_invalid_credentials()
    test_refresh_token()
    test_refresh_invalid_token()
    test_get_current_user()
    test_get_current_user_invalid_token()
    print("\nAll authentication tests passed!")