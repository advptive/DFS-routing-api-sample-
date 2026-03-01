from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Volunteer Routing API is running"}


def test_overweight_validation():
    payload = {
        "start_coords": [50.0, 30.0],
        "max_capacity": 500.0,
        "tasks": [
            {
                "id": 99,
                "pickup_coords": [50.1, 30.1],
                "dropoff_coords": [50.2, 30.2],
                "weight": 600.0
            }
        ]
    }

    response = client.post("/api/v1/optimize-route", json=payload)

    assert response.status_code == 400
    assert "занадто важка" in response.json()["detail"]


def test_successful_route_optimization():
    payload = {
        "start_coords": [50.4501, 30.5234],
        "max_capacity": 500.0,
        "tasks": [
            {
                "id": 1,
                "pickup_coords": [50.4600, 30.5100],
                "dropoff_coords": [50.4000, 30.6000],
                "weight": 200.0
            }
        ]
    }

    response = client.post("/api/v1/optimize-route", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert len(data["optimal_path_indices"]) == 3
    assert data["total_road_distance_km"] > 0