# Forecasting Tool Microservice

A Python-based microservice for forecasting PV production using physics-based simulations.

## Features

- **7-Day PV Production Forecasting**: Uses `pvlib` to simulate PV panel performance based on location, panel configuration, and temperature effects.
- **Multi-User Support**: JWT-based authentication with user isolation for PV systems in a cloud environment.
- **Weather Integration**: Automatically fetches high-precision solar irradiance (GHI, DNI) and weather data from the OpenMeteo API.
- **Production-Ready**: Comprehensive test suite with 100% test coverage and stabilized implementation.

## API Documentation

### Base URL
`http://localhost:8084` (or the URL of the cloud deployment).

### Authentication
All endpoints require a valid `Authorization` header containing a JWT token, which is provided by the backend gateway.
`Authorization: Bearer <your_jwt_token>`

---

### 1. PV System Management

#### `POST /systems`
Creates a new PV system for the authenticated user.

*   **Request Body**:
    ```json
    {
      "name": "Main Roof South",
      "latitude": 48.2082,
      "longitude": 16.3738,
      "kwp": 8.5,
      "tilt": 35,
      "azimuth": 180
    }
    ```
*   **Response (201 Created)**:
    ```json
    {
      "id": 123,
      "name": "Main Roof South",
      "latitude": 48.2082,
      "longitude": 16.3738,
      "kwp": 8.5,
      "tilt": 35,
      "azimuth": 180,
      "user_id": "user-uuid-xyz"
    }
    ```

##### PV System Data Model
| Parameter | Type | Unit | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | - | Unique identifier for the system (auto-generated). |
| `name` | String | - | User-defined name for the system. |
| `latitude` | Float | Degrees (°) | Geographic latitude of the system's location (-90° to +90°). Positive = Northern Hemisphere, Negative = Southern Hemisphere. |
| `longitude` | Float | Degrees (°) | Geographic longitude of the system's location (-180° to +180°). Positive = Eastern Hemisphere, Negative = Western Hemisphere. |
| `kwp` | Float | Kilowatts peak (kWp) | Installed peak power of the PV system. |
| `tilt` | Float | Degrees (°) | Tilt angle of the panels from horizontal. |
| `azimuth` | Float | Degrees (°) | Orientation of the panels (0°=N, 90°=E, 180°=S, 270°=W). |
| `user_id` | String | UUID | The unique identifier of the user who owns the system. |

#### `GET /systems`
Lists all PV systems for the authenticated user.

*   **Response (200 OK)**:
    ```json
    [
      { "id": 123, "name": "Main Roof South", "kwp": 8.5, "azimuth": 180 },
      { "id": 124, "name": "Carport West", "kwp": 2.5, "azimuth": 260 }
    ]
    ```

---

### 3. Forecasting

#### `POST /forecast/production/{system_id}`
Generates a 7-day PV production forecast for a specific system belonging to the user.

*   **URL Parameter**: `system_id` (integer) - The ID of the PV system.
*   **Request Body** (optional - defaults to 7 days):
    ```json
    {
      "days": 7
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "system_id": 123,
      "total_energy_kwh": 45.2,
      "forecast_from": "2024-01-02T00:00:00Z",
      "forecast_to": "2024-01-09T00:00:00Z",
      "forecast_hours": 168,
      "forecast_list": [
        {
          "day": "2024-01-02T",
          "daily_energy_kwh": 45.2,
          "forecast": [
{
          "day": "2024-01-02T",
          "daily_energy_kwh": 45.2,
          "forecast": [
            { 
              "timestamp": "2024-01-02T12:00:00Z", 
              "power_kw": 4.5
            },
            { 
              "timestamp": "2024-01-02T13:00:00Z", 
              "power_kw": 5.1
            }
            // ... 22 weitere Stunden für diesen Tag
          ]
        },
            { 
              "timestamp": "2024-01-02T13:00:00Z", 
              "power_kw": 5.1
            }
            // ... 22 further hours day 1 
          ]
        },
        {
          "day": "2024-01-03T",
          "forecast": [
            // 24 h of day 2 
          ]
        }
        // ... 7 days overall 
      ]
    }
    ```

##### Forecast Data Model
| Parameter | Type | Unit | Description |
| :--- | :--- | :--- | :--- |
| `system_id` | Integer | - | The ID of the PV system this forecast is for. |
| `total_energy_kwh` | Float | Kilowatt-hours (kWh) | Total energy predicted to be generated. |
| `forecast_from` | String | ISO 8601 | The start timestamp of the forecast period (UTC). |
| `forecast_to` | String | ISO 8601 | The end timestamp of the forecast period (UTC). |
| `forecast_hours` | Integer | Hours | Total number of forecast hours (always 168 for 7 days). |
| `forecast_list` | Array | - | A list of daily forecasts (7 days × 24 hours). |
| `daily_energy_kwh` | Float | Kilowatt-hours (kWh) | Total energy for this day. |
| `day` | String | - | Date in YYYY-MM-T format for day. |
| `forecast` | Array | - | 24 hourly forecast points for this day. |
| `timestamp` | String | ISO 8601 | The UTC timestamp for the forecast point. |
| `power_kw` | Float | Kilowatts (kW) | The predicted AC power output at the given timestamp. |

---

---

### Error Handling

The service uses standard HTTP status codes.
*   `400 Bad Request`: Missing or invalid input data.
*   `401 Unauthorized`: Missing or invalid `Authorization` header.
*   `403 Forbidden`: User trying to access a resource that does not belong to them.
*   `404 Not Found`: The requested resource (system, device) was not found.
*   `500 Internal Server Error`: An unexpected error on the server.

Error responses follow this format:
```json
{
  "detail": "A descriptive error message for the developer."
}
```

## Database Architecture

This service uses **SQLite** as its database. The choice was made for maximum simplicity, portability, and ease of local development.

### Data Storage
The database is a single file, `forecasting.db`, which is stored within the service's file system. All user configurations and PV systems are persisted in this file.

### Operational Considerations for Cloud Deployment

When deploying this service in a cloud environment, please be aware of the following critical points:

*   **Persistence**: The `forecasting.db` file **must be persisted**. If the service is running in a container, you must use a persistent volume (e.g., a Docker Volume or a Kubernetes PersistentVolumeClaim) to mount the database file. Without this, the entire database will be lost every time the container is restarted or redeployed.

*   **Backups**: This service does not perform automated backups. It is the operator's responsibility to implement a backup strategy for the `forecasting.db` file. A common approach is to have a periodic cron job or a sidecar container that copies the database file to a durable object storage service (e.g., AWS S3, Google Cloud Storage).

*   **Scalability & Data Consistency**: SQLite is a file-based database and is not designed for high-concurrency write access from multiple service instances. **If you scale this service to run more than one instance behind a load balancer, each instance will have its own separate `forecasting.db` file. This will lead to data inconsistency between instances.** This architecture is therefore best suited for a single-instance deployment or for read-heavy workloads where write conflicts are rare.

*   **Concurrency**: Under heavy write load from multiple users, you may experience "database is locked" errors. This is a limitation of SQLite. If your application anticipates high write concurrency, consider migrating to a client-server database like PostgreSQL.

## Development

### Prerequisites
- Python 3.10+ (tested with 3.13)
- `pvlib`, `fastapi`, `uvicorn`, `requests`, `pandas`, `sqlalchemy`

### Setup
```bash
# Create venv
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running
```bash
# Start server with auto-reload
uvicorn app.main:app --reload --port 8084
```

### Testing
```bash
# Run all tests (52 tests, 100% pass rate)
pytest

# Run tests with coverage
pytest --cov=app --cov-report=xml --junitxml=test-results.xml

# Run specific test file
pytest tests/test_weather_client.py -v

# Run specific test
pytest tests/test_forecasting_models.py::TestForecastingModels::test_forecast_request_valid_days_in_range -v
```

## Architecture
This service is designed to be stateless in its application logic. It relies on a persistent SQLite database file to store user configurations and does not store state in memory between requests.

### Current Implementation Status
- ✅ **7-Day PV Forecasting**: Full hourly forecasting with daily grouping and weather integration
- ✅ **JWT Authentication**: User isolation and automatic user creation
- ✅ **PV System Management**: CRUD operations for PV systems
- ✅ **Hierarchical Response Structure**: Daily grouped forecast data (7 days × 24 hours)
- ✅ **Test Suite**: 52 tests with 100% pass rate

### Authentication
The service validates JWT tokens using the shared secret key `voltcast-shared-secret-key-2024` and automatically creates user records in the local database on first successful authentication.
