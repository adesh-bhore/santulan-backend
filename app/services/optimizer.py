"""Optimizer Service

Uses Google OR-Tools CP-SAT solver to find optimal vehicle and driver assignments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import math

from ortools.sat.python import cp_model

from app.services.tsn_builder import TSNGraph, TSNNode, TSNEdge
from app.models.base_models import Vehicle, Driver


@dataclass
class OptimizationMetrics:
    """Metrics from optimization result"""
    fleet_size: int
    total_deadhead_km: float
    estimated_emissions_kg: float
    duty_variance_minutes: float
    trips_covered: int
    trips_total: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'fleet_size': self.fleet_size,
            'total_deadhead_km': round(self.total_deadhead_km, 2),
            'estimated_emissions_kg': round(self.estimated_emissions_kg, 2),
            'duty_variance_minutes': round(self.duty_variance_minutes, 2),
            'trips_covered': self.trips_covered,
            'trips_total': self.trips_total
        }


@dataclass
class OptimizationResult:
    """Result of optimization run"""
    vehicle_assignments: Dict[str, List[str]]  # vehicle_id → [trip_ids]
    driver_assignments: Dict[str, List[str]]   # driver_id → [trip_ids]
    metrics: OptimizationMetrics
    solver_status: str
    solver_time_seconds: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'vehicle_assignments': self.vehicle_assignments,
            'driver_assignments': self.driver_assignments,
            'metrics': self.metrics.to_dict(),
            'solver_status': self.solver_status,
            'solver_time_seconds': round(self.solver_time_seconds, 2)
        }


class Optimizer:
    """OR-Tools CP-SAT optimizer for vehicle and driver scheduling"""
    
    def __init__(self):
        self.default_time_limit_seconds = 120
        self.break_requirement_hours = 0.5  # 30 minutes break after 4 hours
        self.break_trigger_hours = 4.0
    
    def optimize(
        self,
        tsn: TSNGraph,
        vehicles: List[Vehicle],
        drivers: List[Driver],
        objective_weights: Optional[Dict[str, float]] = None,
        time_limit_seconds: Optional[int] = None
    ) -> OptimizationResult:
        """
        Run CP-SAT optimization on Time-Space Network.
        
        Args:
            tsn: Time-Space Network graph
            vehicles: Available vehicles for depot
            drivers: Available drivers for depot
            objective_weights: Weights for objective function components
            time_limit_seconds: Solver time limit (default: 120)
        
        Returns:
            OptimizationResult with assignments and metrics
        """
        # Set defaults
        if objective_weights is None:
            objective_weights = {
                'fleet_size': 100.0,
                'deadhead': 10.0,
                'emissions': 5.0,
                'duty_variance': 1.0
            }
        
        if time_limit_seconds is None:
            time_limit_seconds = self.default_time_limit_seconds
        
        # Extract trip edges from TSN
        trip_edges = [e for e in tsn.edges if e.edge_type == "trip"]
        trip_ids = [e.metadata['trip_id'] for e in trip_edges]
        
        if not trip_ids:
            raise ValueError("No trips found in TSN")
        
        print(f"  Optimizing {len(trip_ids)} trips with {len(vehicles)} vehicles and {len(drivers)} drivers...")
        
        # PERFORMANCE OPTIMIZATION: For large depots (>500 trips), use greedy heuristic
        if len(trip_ids) > 500:
            print(f"  🚀 Large depot detected ({len(trip_ids)} trips) - using fast greedy heuristic")
            return self._greedy_optimize(
                trip_edges, vehicles, drivers, objective_weights
            )
        
        # For smaller depots, use CP-SAT solver
        return self._cpsat_optimize(
            trip_edges, trip_ids, vehicles, drivers, 
            objective_weights, time_limit_seconds
        )
        
        # Decision variables
        vehicle_trip = {}  # vehicle_trip[v][t]: Binary, 1 if vehicle v covers trip t
        driver_trip = {}   # driver_trip[d][t]: Binary, 1 if driver d covers trip t
        vehicle_used = {}  # vehicle_used[v]: Binary, 1 if vehicle v is used
        
        # Create variables
        for vehicle in vehicles:
            vehicle_used[vehicle.vehicle_id] = model.NewBoolVar(f'vehicle_used_{vehicle.vehicle_id}')
            vehicle_trip[vehicle.vehicle_id] = {}
            for trip_id in trip_ids:
                vehicle_trip[vehicle.vehicle_id][trip_id] = model.NewBoolVar(
                    f'vehicle_{vehicle.vehicle_id}_trip_{trip_id}'
                )
        
        for driver in drivers:
            driver_trip[driver.driver_id] = {}
            for trip_id in trip_ids:
                driver_trip[driver.driver_id][trip_id] = model.NewBoolVar(
                    f'driver_{driver.driver_id}_trip_{trip_id}'
                )
        
        # CONSTRAINT 1: Trip Coverage
        # Each trip must be covered by exactly one vehicle and one driver
        for trip_id in trip_ids:
            model.Add(
                sum(vehicle_trip[v.vehicle_id][trip_id] for v in vehicles) == 1
            )
            model.Add(
                sum(driver_trip[d.driver_id][trip_id] for d in drivers) == 1
            )
        
        # CONSTRAINT 2: Vehicle Usage
        # If vehicle covers any trip, it must be marked as used
        for vehicle in vehicles:
            for trip_id in trip_ids:
                model.Add(
                    vehicle_trip[vehicle.vehicle_id][trip_id] <= vehicle_used[vehicle.vehicle_id]
                )
        
        # CONSTRAINT 3: Vehicle Trip Limits
        # Each vehicle can only do a realistic number of trips per day
        # Calculate dynamic limit based on available vehicles and trips
        # Minimum: 12 trips/vehicle (ideal scenario)
        # Maximum: Adjust upward if needed to make problem feasible
        min_trips_per_vehicle = 12
        required_vehicles = math.ceil(len(trip_ids) / min_trips_per_vehicle)
        
        if required_vehicles > len(vehicles):
            # Need to increase trips per vehicle to make problem feasible
            max_trips_per_vehicle = math.ceil(len(trip_ids) / len(vehicles)) + 2  # +2 for buffer
            print(f"  ⚠️  Adjusting max_trips_per_vehicle to {max_trips_per_vehicle} (need {required_vehicles} vehicles, have {len(vehicles)})")
        else:
            max_trips_per_vehicle = min_trips_per_vehicle
        
        for vehicle in vehicles:
            total_trips = sum(
                vehicle_trip[vehicle.vehicle_id][trip_id]
                for trip_id in trip_ids
            )
            model.Add(total_trips <= max_trips_per_vehicle)
        
        # CONSTRAINT 4: Driver Duty Limits
        # Total duty time for each driver must not exceed max_duty_hours
        # Make this constraint more flexible to avoid infeasibility
        trip_durations = {}
        for edge in trip_edges:
            trip_id = edge.metadata['trip_id']
            duration_minutes = edge.metadata.get('duration_minutes', 30)  # Default 30 min
            trip_durations[trip_id] = int(duration_minutes)  # Ensure integer
        
        # Calculate if driver constraints might cause infeasibility
        total_trip_minutes = sum(trip_durations.values())
        total_driver_capacity_minutes = sum(int(float(d.max_duty_hours) * 60) for d in drivers)
        
        if total_trip_minutes > total_driver_capacity_minutes:
            print(f"  ⚠️  Total trip time ({total_trip_minutes}min) exceeds driver capacity ({total_driver_capacity_minutes}min)")
            print(f"  ⚠️  Relaxing driver duty constraints by 20% to make problem feasible")
            duty_multiplier = 1.2  # Allow 20% overtime
        else:
            duty_multiplier = 1.0
        
        for driver in drivers:
            total_duty_minutes = sum(
                driver_trip[driver.driver_id][trip_id] * trip_durations[trip_id]
                for trip_id in trip_ids
            )
            max_duty_minutes = int(float(driver.max_duty_hours) * 60 * duty_multiplier)
            model.Add(total_duty_minutes <= max_duty_minutes)
        
        # OBJECTIVE: Minimize weighted sum
        objective_terms = []
        
        # Term 1: Fleet size (number of vehicles used)
        fleet_size_term = sum(vehicle_used[v.vehicle_id] for v in vehicles)
        objective_terms.append(
            int(objective_weights['fleet_size'] * 1000) * fleet_size_term
        )
        
        # Term 2: Deadhead distance
        # Simplified: count deadhead edges used (actual implementation would track paths)
        deadhead_edges = [e for e in tsn.edges if e.edge_type == "deadhead"]
        deadhead_cost = len(deadhead_edges) * 10  # Placeholder
        # Note: Full implementation would track which deadhead edges are used
        
        # Term 3: Emissions (proportional to fleet size and distance)
        # Simplified: use fleet size as proxy
        emissions_term = fleet_size_term
        objective_terms.append(
            int(objective_weights['emissions'] * 100) * emissions_term
        )
        
        # Minimize objective
        model.Minimize(sum(objective_terms))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.log_search_progress = False
        
        start_time = datetime.now()
        status = solver.Solve(model)
        solve_time = (datetime.now() - start_time).total_seconds()
        
        # Extract solution
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            vehicle_assignments = self._extract_vehicle_assignments(
                solver, vehicle_trip, vehicles, trip_ids
            )
            driver_assignments = self._extract_driver_assignments(
                solver, driver_trip, drivers, trip_ids
            )
            
            # Calculate metrics
            metrics = self._calculate_metrics(
                vehicle_assignments,
                driver_assignments,
                trip_durations,
                vehicles,
                len(trip_ids)
            )
            
            status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
            
            return OptimizationResult(
                vehicle_assignments=vehicle_assignments,
                driver_assignments=driver_assignments,
                metrics=metrics,
                solver_status=status_str,
                solver_time_seconds=solve_time
            )
        else:
            # No solution found
            status_map = {
                cp_model.INFEASIBLE: "INFEASIBLE",
                cp_model.MODEL_INVALID: "MODEL_INVALID",
                cp_model.UNKNOWN: "UNKNOWN"
            }
            status_str = status_map.get(status, "UNKNOWN")
            
            raise ValueError(f"Optimization failed with status: {status_str}")
    
    def _cpsat_optimize(
        self,
        trip_edges: List[TSNEdge],
        trip_ids: List[str],
        vehicles: List[Vehicle],
        drivers: List[Driver],
        objective_weights: Dict[str, float],
        time_limit_seconds: int
    ) -> OptimizationResult:
        """CP-SAT solver for small/medium depots (<500 trips)"""
        
        # Create CP-SAT model
        model = cp_model.CpModel()
        self,
        solver: cp_model.CpSolver,
        vehicle_trip: Dict,
        vehicles: List[Vehicle],
        trip_ids: List[str]
    ) -> Dict[str, List[str]]:
        """Extract vehicle assignments from solver solution"""
        assignments = {}
        
        for vehicle in vehicles:
            assigned_trips = []
            for trip_id in trip_ids:
                if solver.Value(vehicle_trip[vehicle.vehicle_id][trip_id]) == 1:
                    assigned_trips.append(trip_id)
            
            if assigned_trips:
                assignments[vehicle.vehicle_id] = assigned_trips
        
        return assignments
    
    def _extract_driver_assignments(
        self,
        solver: cp_model.CpSolver,
        driver_trip: Dict,
        drivers: List[Driver],
        trip_ids: List[str]
    ) -> Dict[str, List[str]]:
        """Extract driver assignments from solver solution"""
        assignments = {}
        
        for driver in drivers:
            assigned_trips = []
            for trip_id in trip_ids:
                if solver.Value(driver_trip[driver.driver_id][trip_id]) == 1:
                    assigned_trips.append(trip_id)
            
            if assigned_trips:
                assignments[driver.driver_id] = assigned_trips
        
        return assignments
    
    def _calculate_metrics(
        self,
        vehicle_assignments: Dict[str, List[str]],
        driver_assignments: Dict[str, List[str]],
        trip_durations: Dict[str, float],
        vehicles: List[Vehicle],
        total_trips: int
    ) -> OptimizationMetrics:
        """Calculate optimization metrics from assignments"""
        
        # Fleet size
        fleet_size = len(vehicle_assignments)
        
        # Trips covered
        trips_covered = sum(len(trips) for trips in vehicle_assignments.values())
        
        # Deadhead (simplified - would need path tracking for accuracy)
        total_deadhead_km = fleet_size * 5.0  # Placeholder: 5km per vehicle
        
        # Emissions (simplified)
        avg_emission_factor = 2.68  # kg CO2 per km
        if vehicles:
            avg_emission_factor = sum(float(v.emission_factor) for v in vehicles) / len(vehicles)
        estimated_emissions_kg = total_deadhead_km * avg_emission_factor
        
        # Duty variance
        driver_duty_times = []
        for driver_id, trips in driver_assignments.items():
            total_minutes = sum(trip_durations.get(trip_id, 30) for trip_id in trips)
            driver_duty_times.append(total_minutes)
        
        if driver_duty_times:
            mean_duty = sum(driver_duty_times) / len(driver_duty_times)
            variance = sum((t - mean_duty) ** 2 for t in driver_duty_times) / len(driver_duty_times)
            duty_variance_minutes = math.sqrt(variance)
        else:
            duty_variance_minutes = 0.0
        
        return OptimizationMetrics(
            fleet_size=fleet_size,
            total_deadhead_km=total_deadhead_km,
            estimated_emissions_kg=estimated_emissions_kg,
            duty_variance_minutes=duty_variance_minutes,
            trips_covered=trips_covered,
            trips_total=total_trips
        )
