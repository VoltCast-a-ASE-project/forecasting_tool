# Forecasting Tool Microservice

A Python-based microservice for forecasting PV production and optimizing device usage times using physics-based simulations.

## Features

- **Physics-Based Forecasting**: Uses `pvlib` to simulate PV panel performance based on location, panel configuration, and temperature effects.
- **Multi-User Support**: Manages multiple PV systems and devices for different users in a cloud environment.
- **Optimization**: Calculates the best time window to run high-consumption devices (EVs, Washing Machines) to maximize solar self-consumption.
- **Weather Integration**: Automatically fetches high-precision solar irradiance (GHI, DNI) and weather data from the OpenMeteo API.

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
| `latitude` | Float | Degrees (°) | Geographic latitude of the system's location. |
| `longitude` | Float | Degrees (°) | Geographic longitude of the system's location. |
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

### 2. Device Management

#### `POST /devices`
Creates a new device (e.g., EV, washing machine) for the authenticated user.

*   **Request Body**:
    ```json
    {
      "name": "Tesla Model 3",
      "type": "ev",
      "power_kw": 11.0,
      "total_energy_kwh": 50.0
    }
    ```
*   **Response (201 Created)**:
    ```json
    {
      "id": 456,
      "name": "Tesla Model 3",
      "type": "ev",
      "power_kw": 11.0,
      "total_energy_kwh": 50.0,
      "user_id": "user-uuid-xyz"
    }
    ```

##### Device Data Model
| Parameter | Type | Unit | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | - | Unique identifier for the device (auto-generated). |
| `name` | String | - | User-defined name for the device. |
| `type` | String | - | Category of the device (e.g., "ev", "washer", "dryer"). |
| `power_kw` | Float | Kilowatts (kW) | Maximum power consumption of the device. |
| `total_energy_kwh` | Float | Kilowatt-hours (kWh) | Total energy required for one full cycle. |
| `user_id` | String | UUID | The unique identifier of the user who owns the device. |

#### `GET /devices`
Lists all devices for the authenticated user.

*   **Response (200 OK)**:
    ```json
    [
      { "id": 456, "name": "Tesla Model 3", "type": "ev", "power_kw": 11.0 },
      { "id": 457, "name": "Washing Machine", "type": "washer", "power_kw": 2.0 }
    ]
    ```

---

### 3. Forecasting

#### `POST /forecast/production/{system_id}`
Generates a PV production forecast for a specific system belonging to the user.

*   **URL Parameter**: `system_id` (integer) - The ID of the PV system.
*   **Request Body**:
    ```json
    {
      "days": 2
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "system_id": 123,
      "total_energy_kwh": 45.2,
      "forecast": [
        { "timestamp": "2023-10-27T12:00:00Z", "power_kw": 4.5 },
        { "timestamp": "2023-10-27T13:00:00Z", "power_kw": 5.1 }
      ]
    }
    ```

##### Forecast Data Model
| Parameter | Type | Unit | Description |
| :--- | :--- | :--- | :--- |
| `system_id` | Integer | - | The ID of the PV system this forecast is for. |
| `days` | Integer | Days | Number of days to forecast into the future (1-7). |
| `total_energy_kwh` | Float | Kilowatt-hours (kWh) | Total energy predicted to be generated. |
| `forecast` | Array | - | A list of forecast points. |
| `timestamp` | String | ISO 8601 | The UTC timestamp for the forecast point. |
| `power_kw` | Float | Kilowatts (kW) | The predicted AC power output at the given timestamp. |

---

### 4. Device Optimization

#### `POST /forecast/optimal-time/{device_id}`
Calculates the optimal start time for a device to maximize solar self-consumption.

*   **URL Parameter**: `device_id` (integer) - The ID of the device.
*   **Request Body**:
    ```json
    {
      "system_id": 123,
      "days_lookahead": 1
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "device_id": 456,
      "system_id": 123,
      "start_time": "2023-10-27T10:00:00Z",
      "end_time": "2023-10-27T14:00:00Z",
      "solar_power_used_kwh": 18.5,
      "grid_power_needed_kwh": 1.5
    }
    ```

##### Optimization Data Model
| Parameter | Type | Unit | Description |
| :--- | :--- | :--- | :--- |
| `device_id` | Integer | - | The ID of the device this optimization is for. |
| `system_id` | Integer | - | The ID of the PV system used for the forecast. |
| `days_lookahead` | Integer | Days | The number of days ahead to search for an optimal window. |
| `start_time` | String | ISO 8601 | The recommended start time for device operation (UTC). |
| `end_time` | String | ISO 8601 | The recommended end time for device operation (UTC). |
| `solar_power_used_kwh` | Float | Kilowatt-hours (kWh) | Energy covered by solar power. |
| `grid_power_needed_kwh` | Float | Kilowatt-hours (kWh) | Energy that must be drawn from the grid. |

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
The database is a single file, `forecasting.db`, which is stored within the service's file system. All user configurations, PV systems, and devices are persisted in this file.

### Operational Considerations for Cloud Deployment

When deploying this service in a cloud environment, please be aware of the following critical points:

*   **Persistence**: The `forecasting.db` file **must be persisted**. If the service is running in a container, you must use a persistent volume (e.g., a Docker Volume or a Kubernetes PersistentVolumeClaim) to mount the database file. Without this, the entire database will be lost every time the container is restarted or redeployed.

*   **Backups**: This service does not perform automated backups. It is the operator's responsibility to implement a backup strategy for the `forecasting.db` file. A common approach is to have a periodic cron job or a sidecar container that copies the database file to a durable object storage service (e.g., AWS S3, Google Cloud Storage).

*   **Scalability & Data Consistency**: SQLite is a file-based database and is not designed for high-concurrency write access from multiple service instances. **If you scale this service to run more than one instance behind a load balancer, each instance will have its own separate `forecasting.db` file. This will lead to data inconsistency between instances.** This architecture is therefore best suited for a single-instance deployment or for read-heavy workloads where write conflicts are rare.

*   **Concurrency**: Under heavy write load from multiple users, you may experience "database is locked" errors. This is a limitation of SQLite. If your application anticipates high write concurrency, consider migrating to a client-server database like PostgreSQL.

## Development

### Prerequisites
- Python 3.10+
- `pvlib`, `fastapi`, `uvicorn`, `requests`, `pandas`, `pyyaml`, `sqlalchemy`

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
# Run all tests
pytest

# Run specific test file
pytest tests/test_weather_client.py -v
```

## Architecture
This service is designed to be stateless in its application logic. It relies on a persistent SQLite database file to store user configurations and does not store state in memory between requests.