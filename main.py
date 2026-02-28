import os
import requests
import numpy as np
from typing import List, Tuple, Dict, Set
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from geopy.distance import geodesic


OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org")
MAX_TASKS_LIMIT = int(os.getenv("MAX_TASKS_LIMIT", "7"))



class Task(BaseModel):
    id: int
    pickup_coords: Tuple[float, float]
    dropoff_coords: Tuple[float, float]
    weight: float


class RouteRequest(BaseModel):
    start_coords: Tuple[float, float]
    max_capacity: float
    tasks: List[Task]


class RouteResponse(BaseModel):
    status: str
    optimal_path_indices: List[int]
    human_readable_steps: List[str]
    total_road_distance_km: float


# logic
class RouteOptimizer:
    def __init__(self, start_coords: Tuple[float, float], tasks: List[Task], max_capacity: float):
        self.start_coords = start_coords
        self.tasks = tasks
        self.max_capacity = max_capacity
        self.num_tasks = len(tasks)
        self.total_nodes = 2 * self.num_tasks + 1

        self.best_distance = float('inf')
        self.best_path: List[int] = []

        self.distance_matrix = np.zeros((self.total_nodes, self.total_nodes))
        self.node_mapping = self._build_node_mapping()
        self._build_road_distance_matrix()

    def _build_node_mapping(self) -> Dict[int, Tuple[float, float]]:
        mapping = {0: self.start_coords}
        for i, task in enumerate(self.tasks):
            mapping[i + 1] = task.pickup_coords
            mapping[i + 1 + self.num_tasks] = task.dropoff_coords
        return mapping

    def _build_road_distance_matrix(self):
        coords_list = []
        for i in range(self.total_nodes):
            lat, lon = self.node_mapping[i]
            coords_list.append(f"{lon},{lat}")

        coords_str = ";".join(coords_list)
        url = f"{OSRM_BASE_URL}/table/v1/driving/{coords_str}?annotations=distance"

        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok":
                    self.distance_matrix = np.array(data["distances"]) / 1000.0
                    print(" Маршрут побудовано(OSRM)")
                    return
        except requests.exceptions.RequestException:
            pass

        # if OSRM crashed or did not respond
        print("OSRM недоступний, Використовуємо геодезичні")
        for i in range(self.total_nodes):
            for j in range(self.total_nodes):
                if i != j:
                    self.distance_matrix[i][j] = geodesic(self.node_mapping[i], self.node_mapping[j]).kilometers

# DFS
    def _dfs_search(self, current_node: int, visited: Set[int], current_load: float, current_dist: float,
                    path: List[int]):
        if current_dist >= self.best_distance:
            return

        if len(visited) == self.total_nodes:
            self.best_distance = current_dist
            self.best_path = list(path)
            return

        for next_node in range(1, self.total_nodes):
            if next_node not in visited:
                is_pickup = 1 <= next_node <= self.num_tasks
                is_delivery = next_node > self.num_tasks

                if is_pickup:
                    task_idx = next_node - 1
                    task_weight = self.tasks[task_idx].weight

                    if current_load + task_weight <= self.max_capacity:
                        visited.add(next_node)
                        path.append(next_node)
                        self._dfs_search(next_node, visited, current_load + task_weight,
                                         current_dist + self.distance_matrix[current_node][next_node], path)
                        path.pop()
                        visited.remove(next_node)

                elif is_delivery:
                    task_idx = next_node - self.num_tasks - 1
                    corresponding_pickup = task_idx + 1
                    task_weight = self.tasks[task_idx].weight

                    if corresponding_pickup in visited:
                        visited.add(next_node)
                        path.append(next_node)
                        self._dfs_search(next_node, visited, current_load - task_weight,
                                         current_dist + self.distance_matrix[current_node][next_node], path)
                        path.pop()
                        visited.remove(next_node)

    def optimize(self):
        self._dfs_search(current_node=0, visited={0}, current_load=0.0, current_dist=0.0, path=[0])

        if not self.best_path:
            return None

        result_steps = []
        for node in self.best_path:
            if node == 0:
                result_steps.append("Старт")
            elif 1 <= node <= self.num_tasks:
                result_steps.append(f"Забрати заявку #{self.tasks[node - 1].id} (+{self.tasks[node - 1].weight} кг)")
            else:
                task_idx = node - self.num_tasks - 1
                result_steps.append(f"Віддати заявку #{self.tasks[task_idx].id} (-{self.tasks[task_idx].weight} кг)")

        return {
            "optimal_path_indices": self.best_path,
            "human_readable_steps": result_steps,
            "total_road_distance_km": round(self.best_distance, 2)
        }


# --- ІНІЦІАЛІЗАЦІЯ ДОДАТКУ ---
app = FastAPI(title="Routing Optimization API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Volunteer Routing API is running"}


@app.post("/api/v1/optimize-route", response_model=RouteResponse)
def optimize_route_endpoint(request: RouteRequest):
    if len(request.tasks) > MAX_TASKS_LIMIT:
        raise HTTPException(status_code=400, detail=f"Перевищено ліміт. Максимум заявок: {MAX_TASKS_LIMIT}")

    try:
        optimizer = RouteOptimizer(
            start_coords=request.start_coords,
            tasks=request.tasks,
            max_capacity=request.max_capacity
        )
        result = optimizer.optimize()

        if not result:
            raise HTTPException(status_code=422,
                                detail="Неможливо прокласти маршрут (можливо, вантаж перевищує ліміт авто).")

        return RouteResponse(
            status="success",
            optimal_path_indices=result["optimal_path_indices"],
            human_readable_steps=result["human_readable_steps"],
            total_road_distance_km=result["total_road_distance_km"]
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Внутрішня помилка сервера під час розрахунків.")