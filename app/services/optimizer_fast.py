"""Fast Optimizer Service with Greedy Heuristic

Uses greedy heuristic for large depots (>500 trips) and CP-SAT for smaller ones.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import math

from ortools.sat.python import cp_model

from app.services.tsn_builder import TSNGraph, TSNEdge
from app.models.base_models import Vehicle, Driver


@dataclass
class OptimizationMetrics:
    """Metrics from optimization result"""
    fleet_size: int
    drivers_used: int  # NEW: Actual number of drivers assigned
    total_deadhead_km: float
    estimated_emissions_kg: float
    duty_variance_minutes: float
    trips_covered: int
    trips_total: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'fleet_size': self.fleet_size,
            'drivers_used': self.drivers_used,
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


class FastOptimizer:
    """Fast optimizer with greedy heuristic for large depots"""
    
    def __init__(self):
        self.large_depot_threshold = 500  # Not used anymore, keeping for reference
        self.cpsat_time_limit = 300  # 5 minutes for CP-SAT (increased from 120s)
    
    def optimize(
        self,
        tsn: TSNGraph,
        vehicles: List[Vehicle],
        drivers: List[Driver],
        objective_weights: Optional[Dict[str, float]] = None,
        time_limit_seconds: Optional[int] = None
    ) -> OptimizationResult:
        """
        Run CP-SAT optimization for all depot sizes.
        """
        # Extract trip edges
        trip_edges = [e for e in tsn.edges if e.edge_type == "trip"]
        trip_ids = [e.metadata['trip_id'] for e in trip_edges]
        
        if not trip_ids:
            raise ValueError("No trips found in TSN")
        
        print(f"Optimizing {len(trip_ids)} trips with {len(vehicles)} vehicles and {len(drivers)} drivers...")
        print(f"Using CP-SAT solver for {len(trip_ids)} trips")
        
        # Use CP-SAT for all depots
        return self._cpsat_optimize(
            trip_edges, trip_ids, vehicles, drivers, 
            time_limit_seconds or self.cpsat_time_limit
        )
    
    def _greedy_optimize(
        self,
        trip_edges: List[TSNEdge],
        vehicles: List[Vehicle],
        drivers: List[Driver]
    ) -> OptimizationResult:
        """
        Fast greedy heuristic - completes in seconds.
        Round-robin assignment with capacity constraints.
        """
        start_time = datetime.now()
        
        # Sort trips by start time
        sorted_trips = sorted(trip_edges, key=lambda e: e.metadata.get('start_time', '00:00'))
        trip_ids = [e.metadata['trip_id'] for e in sorted_trips]
        
        # Extract trip durations
        trip_durations = {}
        for edge in trip_edges:
            trip_id = edge.metadata['trip_id']
            duration_minutes = edge.metadata.get('duration_minutes', 30)
            trip_durations[trip_id] = int(duration_minutes)
        
        # Initialize
        vehicle_assignments = {v.vehicle_id: [] for v in vehicles}
        driver_assignments = {d.driver_id: [] for d in drivers}
        vehicle_trip_counts = {v.vehicle_id: 0 for v in vehicles}
        driver_duty_minutes = {d.driver_id: 0 for d in drivers}
        driver_max_minutes = {d.driver_id: int(float(d.max_duty_hours) * 60 * 1.2) for d in drivers}
        
        # Calculate limits
        max_trips_per_vehicle = max(12, math.ceil(len(trip_ids) / len(vehicles)) + 2)
        
        print(f"Greedy: max {max_trips_per_vehicle} trips/vehicle")
        
        # Round-robin assignment
        vehicle_idx = 0
        driver_idx = 0
        
        for trip_id in trip_ids:
            duration = trip_durations[trip_id]
            
            # Find vehicle with capacity
            assigned_vehicle = None
            for _ in range(len(vehicles)):
                vehicle = vehicles[vehicle_idx]
                if vehicle_trip_counts[vehicle.vehicle_id] < max_trips_per_vehicle:
                    assigned_vehicle = vehicle
                    break
                vehicle_idx = (vehicle_idx + 1) % len(vehicles)
            
            if not assigned_vehicle:
                assigned_vehicle = vehicles[0]
            
            # Find driver with capacity
            assigned_driver = None
            for _ in range(len(drivers)):
                driver = drivers[driver_idx]
                if driver_duty_minutes[driver.driver_id] + duration <= driver_max_minutes[driver.driver_id]:
                    assigned_driver = driver
                    break
                driver_idx = (driver_idx + 1) % len(drivers)
            
            if not assigned_driver:
                assigned_driver = min(drivers, key=lambda d: driver_duty_minutes[d.driver_id])
            
            # Assign
            vehicle_assignments[assigned_vehicle.vehicle_id].append(trip_id)
            driver_assignments[assigned_driver.driver_id].append(trip_id)
            vehicle_trip_counts[assigned_vehicle.vehicle_id] += 1
            driver_duty_minutes[assigned_driver.driver_id] += duration
            
            vehicle_idx = (vehicle_idx + 1) % len(vehicles)
            driver_idx = (driver_idx + 1) % len(drivers)
        
        # Remove empty
        vehicle_assignments = {k: v for k, v in vehicle_assignments.items() if v}
        driver_assignments = {k: v for k, v in driver_assignments.items() if v}
        
        # Metrics
        metrics = self._calculate_metrics(
            vehicle_assignments, driver_assignments, trip_durations, vehicles, len(trip_ids)
        )
        
        solve_time = (datetime.now() - start_time).total_seconds()
        print(f"Greedy complete: {metrics.fleet_size} vehicles, {solve_time:.2f}s")
        
        return OptimizationResult(
            vehicle_assignments=vehicle_assignments,
            driver_assignments=driver_assignments,
            metrics=metrics,
            solver_status="HEURISTIC",
            solver_time_seconds=solve_time
        )
    
    def _cpsat_optimize(
        self,
        trip_edges: List[TSNEdge],
        trip_ids: List[str],
        vehicles: List[Vehicle],
        drivers: List[Driver],
        time_limit_seconds: int
    ) -> OptimizationResult:
        """CP-SAT solver with realistic PMPML constraints"""
        start_time = datetime.now()
        
        # Extract durations
        trip_durations = {}
        for edge in trip_edges:
            trip_id = edge.metadata['trip_id']
            duration_minutes = edge.metadata.get('duration_minutes', 30)
            trip_durations[trip_id] = int(duration_minutes)
        
        # Create model
        model = cp_model.CpModel()
        
        # Variables
        vehicle_trip = {}
        driver_trip = {}
        vehicle_used = {}
        driver_used = {}
        
        for vehicle in vehicles:
            vehicle_used[vehicle.vehicle_id] = model.NewBoolVar(f'used_{vehicle.vehicle_id}')
            vehicle_trip[vehicle.vehicle_id] = {}
            for trip_id in trip_ids:
                vehicle_trip[vehicle.vehicle_id][trip_id] = model.NewBoolVar(
                    f'v_{vehicle.vehicle_id}_t_{trip_id}'
                )
        
        for driver in drivers:
            driver_used[driver.driver_id] = model.NewBoolVar(f'driver_used_{driver.driver_id}')
            driver_trip[driver.driver_id] = {}
            for trip_id in trip_ids:
                driver_trip[driver.driver_id][trip_id] = model.NewBoolVar(
                    f'd_{driver.driver_id}_t_{trip_id}'
                )
        
        # CONSTRAINT 1: Each trip must be assigned to exactly one vehicle and one driver
        for trip_id in trip_ids:
            model.Add(sum(vehicle_trip[v.vehicle_id][trip_id] for v in vehicles) == 1)
            model.Add(sum(driver_trip[d.driver_id][trip_id] for d in drivers) == 1)
        
        # CONSTRAINT 2: Link vehicle/driver usage to assignments
        for vehicle in vehicles:
            for trip_id in trip_ids:
                model.Add(vehicle_trip[vehicle.vehicle_id][trip_id] <= vehicle_used[vehicle.vehicle_id])
        
        for driver in drivers:
            for trip_id in trip_ids:
                model.Add(driver_trip[driver.driver_id][trip_id] <= driver_used[driver.driver_id])
        
        # CONSTRAINT 3: Realistic maximum trips per vehicle (10-12 trips per day)
        max_trips_per_vehicle = min(12, max(10, math.ceil(len(trip_ids) / len(vehicles)) + 1))
        for vehicle in vehicles:
            model.Add(sum(vehicle_trip[vehicle.vehicle_id][trip_id] for trip_id in trip_ids) <= max_trips_per_vehicle)
        
        # CONSTRAINT 4: Realistic driver duty hours (BALANCED: 4-9 hours, with 8.5h soft target)
        MIN_DUTY_HOURS = 4.0  # Minimum 4 hours (allows shorter shifts)
        MAX_DUTY_HOURS = 9.0  # Maximum 9 hours (allows some flexibility)
        MAX_TRIPS_PER_DRIVER = 15  # Maximum 15 trips per driver per day (relaxed from 12)
        
        min_duty_minutes = int(MIN_DUTY_HOURS * 60)
        max_duty_minutes = int(MAX_DUTY_HOURS * 60)
        
        for driver in drivers:
            total_duty = sum(driver_trip[driver.driver_id][trip_id] * trip_durations[trip_id] for trip_id in trip_ids)
            trip_count = sum(driver_trip[driver.driver_id][trip_id] for trip_id in trip_ids)
            
            # If driver is used, enforce minimum duty hours
            model.Add(total_duty >= min_duty_minutes).OnlyEnforceIf(driver_used[driver.driver_id])
            model.Add(total_duty == 0).OnlyEnforceIf(driver_used[driver.driver_id].Not())
            
            # Always enforce maximum duty hours
            model.Add(total_duty <= max_duty_minutes)
            
            # Enforce maximum trips per driver
            model.Add(trip_count <= MAX_TRIPS_PER_DRIVER)
        
        # CONSTRAINT 5: Ensure reasonable driver utilization (prevent using too few drivers)
        # Calculate minimum drivers needed based on total work and max duty hours
        total_trip_minutes = sum(trip_durations.values())
        min_drivers_from_hours = math.ceil(total_trip_minutes / max_duty_minutes)
        min_drivers_from_trips = math.ceil(len(trip_ids) / MAX_TRIPS_PER_DRIVER)
        
        # Use the higher value, but allow some flexibility (80% of calculated minimum)
        min_drivers_to_use = max(
            math.ceil(min_drivers_from_hours * 0.8),
            math.ceil(min_drivers_from_trips * 0.8)
        )
        
        drivers_count = sum(driver_used[d.driver_id] for d in drivers)
        model.Add(drivers_count >= min_drivers_to_use)
        
        print(f"🔧 Optimizer Constraints:")
        print(f"   Total trips: {len(trip_ids)}")
        print(f"   Total work: {total_trip_minutes/60:.1f} hours")
        print(f"   Max duty per driver: {MAX_DUTY_HOURS}h ({max_duty_minutes} min)")
        print(f"   Max trips per driver: {MAX_TRIPS_PER_DRIVER}")
        print(f"   Min drivers from hours: {min_drivers_from_hours}")
        print(f"   Min drivers from trips: {min_drivers_from_trips}")
        print(f"   Minimum drivers enforced: {min_drivers_to_use} (with 80% flexibility)")
        print(f"   Available drivers: {len(drivers)}")
        
        # CONSTRAINT 6: Balance workload - minimize variance in driver duty times
        # Create auxiliary variables for duty times
        driver_duty_vars = {}
        for driver in drivers:
            duty_var = model.NewIntVar(0, max_duty_minutes, f'duty_{driver.driver_id}')
            model.Add(duty_var == sum(driver_trip[driver.driver_id][trip_id] * trip_durations[trip_id] for trip_id in trip_ids))
            driver_duty_vars[driver.driver_id] = duty_var
        
        # OBJECTIVE: Multi-objective optimization
        # 1. Minimize fleet size (vehicles) - primary
        # 2. Balance driver workload (minimize duty range) - secondary  
        # 3. Minimize total deadhead/emissions - tertiary
        
        fleet_size = sum(vehicle_used[v.vehicle_id] for v in vehicles)
        
        # For workload balance, minimize max-min difference
        max_duty = model.NewIntVar(0, max_duty_minutes, 'max_duty')
        min_duty = model.NewIntVar(0, max_duty_minutes, 'min_duty')
        
        for driver in drivers:
            model.Add(driver_duty_vars[driver.driver_id] <= max_duty)
            # Only consider used drivers for min duty
            model.Add(driver_duty_vars[driver.driver_id] >= min_duty).OnlyEnforceIf(driver_used[driver.driver_id])
        
        duty_range = max_duty - min_duty
        
        # Weighted objective
        # Fleet size is most important (cost), then workload balance (fairness)
        model.Minimize(
            fleet_size * 100000 +           # Primary: minimize vehicles (cost)
            duty_range * 1000               # Secondary: balance workload (fairness)
        )
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.log_search_progress = False
        status = solver.Solve(model)
        
        solve_time = (datetime.now() - start_time).total_seconds()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            vehicle_assignments = self._extract_assignments(solver, vehicle_trip, vehicles, trip_ids)
            driver_assignments = self._extract_assignments(solver, driver_trip, drivers, trip_ids)
            metrics = self._calculate_metrics(vehicle_assignments, driver_assignments, trip_durations, vehicles, len(trip_ids))
            
            status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
            
            # Log workload distribution
            print(f"📊 Workload Distribution:")
            duty_times = [sum(trip_durations.get(t, 30) for t in trips) / 60.0 for trips in driver_assignments.values()]
            if duty_times:
                print(f"   Min duty: {min(duty_times):.1f}h, Max duty: {max(duty_times):.1f}h, Avg: {sum(duty_times)/len(duty_times):.1f}h")
                print(f"   Drivers used: {len(driver_assignments)}/{len(drivers)}")
            
            return OptimizationResult(
                vehicle_assignments=vehicle_assignments,
                driver_assignments=driver_assignments,
                metrics=metrics,
                solver_status=status_str,
                solver_time_seconds=solve_time
            )
        else:
            raise ValueError(f"CP-SAT failed with status: {status}")
    
    
    def _extract_assignments(self, solver, assignment_vars, resources, trip_ids):
        """Extract assignments from solver"""
        assignments = {}
        for resource in resources:
            resource_id = resource.vehicle_id if hasattr(resource, 'vehicle_id') else resource.driver_id
            assigned_trips = []
            for trip_id in trip_ids:
                if solver.Value(assignment_vars[resource_id][trip_id]) == 1:
                    assigned_trips.append(trip_id)
            if assigned_trips:
                assignments[resource_id] = assigned_trips
        return assignments
    
    def _calculate_metrics(self, vehicle_assignments, driver_assignments, trip_durations, vehicles, total_trips):
        """Calculate metrics"""
        fleet_size = len(vehicle_assignments)
        drivers_used = len(driver_assignments)  # Actual drivers assigned
        trips_covered = sum(len(trips) for trips in vehicle_assignments.values())
        
        # Deadhead is now calculated per-trip in plan_service, so we estimate here
        # Average ~5km deadhead per vehicle per day (will be accurate in database)
        total_deadhead_km = fleet_size * 5.0
        
        # Calculate average emission factor correctly
        avg_emission_factor = 2.68  # Default kg CO2 per km
        if vehicles and len(vehicles) > 0:
            total_emission = sum(float(v.emission_factor) for v in vehicles)
            avg_emission_factor = total_emission / len(vehicles)
        
        # Round emissions to 1 decimal place
        estimated_emissions_kg = round(total_deadhead_km * avg_emission_factor, 1)
        
        driver_duty_times = []
        for trips in driver_assignments.values():
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
            drivers_used=drivers_used,
            total_deadhead_km=total_deadhead_km,
            estimated_emissions_kg=estimated_emissions_kg,
            duty_variance_minutes=duty_variance_minutes,
            trips_covered=trips_covered,
            trips_total=total_trips
        )
