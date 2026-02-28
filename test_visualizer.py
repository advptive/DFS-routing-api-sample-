import requests
import folium
import webbrowser
import os

API_URL = "http://127.0.0.1:8000/api/v1/optimize-route"

# test coordinates
start_point = [49.8397, 24.0297]
tasks = [
    {
        "id": 1,
        "pickup_coords": [49.8450, 24.0250],  # Забрати
        "dropoff_coords": [49.8100, 24.0000],  # Віддати
        "weight": 200
    },
    {
        "id": 2,
        "pickup_coords": [49.8400, 24.0350],  # Забрати
        "dropoff_coords": [49.8500, 24.0400],  # Віддати
        "weight": 400
    }
]

payload = {
    "start_coords": start_point,
    "max_capacity": 500,
    "tasks": tasks
}

print("Відправляємо координати на розрахунок")
response = requests.post(API_URL, json=payload)

if response.status_code != 200:
    print(f"Помилка API: {response.text}")
    exit()

data = response.json()
print(f"Розрахована дистанція: {data['total_road_distance_km']} км")
for step in data['human_readable_steps']:
    print(f" -> {step}")


# according to the algorithm rules: Index 0 - start, 1..N - pickup, N+1..2N - dropoff
num_tasks = len(tasks)
node_coords = {0: start_point}
for i, task in enumerate(tasks):
    node_coords[i + 1] = task["pickup_coords"]
    node_coords[i + 1 + num_tasks] = task["dropoff_coords"]


m = folium.Map(location=start_point, zoom_start=13)


folium.Marker(
    location=start_point, popup="СТАРТ", icon=folium.Icon(color="green", icon="play")
).add_to(m)

for task in tasks:
    folium.Marker(
        location=task["pickup_coords"],
        popup=f"Забрати #{task['id']} ({task['weight']}кг)",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    folium.Marker(
        location=task["dropoff_coords"],
        popup=f"Віддати #{task['id']}",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)


optimal_indices = data["optimal_path_indices"]
route_coords = [node_coords[idx] for idx in optimal_indices]

folium.PolyLine(
    locations=route_coords,
    color="purple",
    weight=4,
    opacity=0.8,
    tooltip="Оптимальний маршрут"
).add_to(m)


html_file = "route_map.html"
m.save(html_file)
print("Відкриває карту в браузері")
webbrowser.open('file://' + os.path.realpath(html_file))