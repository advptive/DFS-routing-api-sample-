***

### Starting the server ###
uvicorn main:app --reload

### Visual testing ### 
python test_visualizer.py

### Running all tests with detailed output ###
pytest -v

### Request Body ### 
{
  "start_coords": [50.4501, 30.5234],
  "max_capacity": 500.0,
  "tasks": [
    {
      "id": 1,
      "pickup_coords": [50.4600, 30.5100],
      "dropoff_coords": [50.4000, 30.6000],
      "weight": 200.0
    },
    {
      "id": 2,
      "pickup_coords": [50.4400, 30.5300],
      "dropoff_coords": [50.4800, 30.4900],
      "weight": 400.0
    }
  ]
}

### Respond ###
{
  "status": "success",
  "optimal_path_indices": [0, 1, 3, 2, 4],
  "human_readable_steps": [
    "Старт",
    "Забрати заявку #1 (+200.0 кг)",
    "Віддати заявку #1 (-200.0 кг)",
    "Забрати заявку #2 (+400.0 кг)",
    "Віддати заявку #2 (-400.0 кг)"
  ],
  "total_road_distance_km": 28.53
}
