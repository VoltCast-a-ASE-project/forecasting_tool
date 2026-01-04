import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models import PVSystem

# Note: We are assuming the existence of Pydantic schemas and a get_current_user dependency.
# These will need to be created for the implementation to pass the tests.

# --- Test Cases ---

def test_create_pv_system_success(client, db_session: Session, test_user, auth_headers):
    """
    Test the successful creation of a PV system via the API.
    """
    # 1. Arrange: Define the payload for a new PV system
    system_data = {
        "name": "Test Roof South",
        "latitude": 48.2082,
        "longitude": 16.3738,
        "kwp": 8.5,
        "tilt": 35,
        "azimuth": 180
    }

    # 2. Act: Make the POST request to the endpoint
    response = client.post("/systems", json=system_data, headers=auth_headers)

    # 3. Assert: Check the response and the database
    assert response.status_code == status.HTTP_201_CREATED
    
    response_data = response.json()
    assert response_data["name"] == "Test Roof South"
    assert response_data["kwp"] == 8.5
    assert response_data["user_id"] == test_user.user_id
    assert "id" in response_data

    # Verify the data is correctly saved in the database
    db_system = db_session.query(PVSystem).filter(PVSystem.id == response_data["id"]).first()
    assert db_system is not None
    assert db_system.name == "Test Roof South"
    assert db_system.user_id == test_user.user_id

def test_create_pv_system_unauthorized(client):
    """
    Test that creating a system without authentication fails.
    """
    # 1. Arrange: Define payload with all required fields but no headers
    system_data = {
        "name": "Unauthorized System",
        "latitude": 48.2082,
        "longitude": 16.3738,
        "kwp": 5.0,
        "tilt": 35.0,
        "azimuth": 180.0
    }

    # 2. Act: Make the POST request without auth headers
    response = client.post("/systems", json=system_data)

    # 3. Assert: The request should be rejected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_pv_system_invalid_data(client, auth_headers):
    """
    Test that creating a system with invalid data (e.g., negative kwp) fails.
    """
    # 1. Arrange: Define payload with invalid data
    system_data = {
        "name": "Invalid System",
        "latitude": 48.2082,
        "longitude": 16.3738,
        "kwp": -5.0, # Invalid
        "tilt": 35,
        "azimuth": 180
    }

    # 2. Act: Make the POST request
    response = client.post("/systems", json=system_data, headers=auth_headers)

    # 3. Assert: The request should be rejected due to validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = response.json()["detail"][0]
    assert "kwp" in detail["loc"]
    assert "greater than 0" in detail["msg"]

def test_get_user_systems_success(client, db_session: Session, test_user, auth_headers):
    """
    Test that a user can retrieve their own systems.
    """
    # 1. Arrange: Create a system for the user in the database
    system = PVSystem(
        name="Pre-created System",
        user_id=test_user.user_id,
        kwp=10.0,
        latitude=48.2082,
        longitude=16.3738,
        tilt=35.0,
        azimuth=180.0
    )
    db_session.add(system)
    db_session.commit()

    # 2. Act: Make the GET request
    response = client.get("/systems", headers=auth_headers)

    # 3. Assert: Check the response
    assert response.status_code == status.HTTP_200_OK
    systems = response.json()
    assert len(systems) == 1
    assert systems[0]["name"] == "Pre-created System"
    assert systems[0]["id"] == system.id

def test_get_user_systems_empty(client, auth_headers):
    """
    Test that a user gets an empty list if they have no systems.
    """
    # 1. Arrange: No systems created for the user

    # 2. Act: Make the GET request
    response = client.get("/systems", headers=auth_headers)

    # 3. Assert: Check the response
    assert response.status_code == status.HTTP_200_OK
    systems = response.json()
    assert len(systems) == 0

def test_create_pv_system_invalid_latitude(client, auth_headers):
    """
    Test that creating a system with invalid latitude fails.
    """
    # 1. Arrange: Define payload with invalid latitude (beyond North Pole)
    system_data = {
        "name": "Invalid Latitude System",
        "latitude": 95.0,  # Invalid: > 90°
        "longitude": 16.3738,
        "kwp": 5.0,
        "tilt": 35.0,
        "azimuth": 180.0
    }

    # 2. Act: Make the POST request
    response = client.post("/systems", json=system_data, headers=auth_headers)

    # 3. Assert: The request should be rejected due to latitude validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = response.json()["detail"][0]
    assert "latitude" in detail["loc"]
    assert "greater than or equal to 90" in detail["msg"] or "less than or equal to 90" in detail["msg"]

def test_create_pv_system_invalid_longitude(client, auth_headers):
    """
    Test that creating a system with invalid longitude fails.
    """
    # 1. Arrange: Define payload with invalid longitude (beyond Date Line)
    system_data = {
        "name": "Invalid Longitude System",
        "latitude": 48.2082,
        "longitude": 190.0,  # Invalid: > 180°
        "kwp": 5.0,
        "tilt": 35.0,
        "azimuth": 180.0
    }

    # 2. Act: Make the POST request
    response = client.post("/systems", json=system_data, headers=auth_headers)

    # 3. Assert: The request should be rejected due to longitude validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = response.json()["detail"][0]
    assert "longitude" in detail["loc"]
    assert "greater than or equal to 180" in detail["msg"] or "less than or equal to 180" in detail["msg"]

def test_create_pv_system_valid_coordinates_at_poles_and_dateline(client, auth_headers):
    """
    Test that systems can be created with coordinates at geographic extremes.
    """
    test_cases = [
        # System at North Pole
        {
            "name": "North Pole System",
            "latitude": 90.0,  # Valid: exactly at North Pole
            "longitude": 0.0,
            "kwp": 5.0,
            "tilt": 90.0,  # Panels horizontal at pole
            "azimuth": 0.0
        },
        # System at South Pole
        {
            "name": "South Pole System", 
            "latitude": -90.0,  # Valid: exactly at South Pole
            "longitude": 180.0,  # Valid: at International Date Line
            "kwp": 5.0,
            "tilt": 90.0,
            "azimuth": 180.0
        },
        # System at International Date Line
        {
            "name": "Date Line System",
            "latitude": 0.0,  # Valid: at equator
            "longitude": 180.0,  # Valid: at International Date Line
            "kwp": 5.0,
            "tilt": 0.0,  # Equatorial installation
            "azimuth": 0.0
        },
        # System in Southern Hemisphere, Western Hemisphere (South America)
        {
            "name": "South America System",
            "latitude": -34.6037,  # Valid: Southern Hemisphere
            "longitude": -58.3816,  # Valid: Western Hemisphere
            "kwp": 5.0,
            "tilt": 35.0,
            "azimuth": 180.0  # South-facing
        }
    ]

    for i, system_data in enumerate(test_cases):
        # 2. Act: Make the POST request
        response = client.post("/systems", json=system_data, headers=auth_headers)
        
        # 3. Assert: The request should succeed
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["name"] == system_data["name"]
        assert response_data["latitude"] == system_data["latitude"]
        assert response_data["longitude"] == system_data["longitude"]