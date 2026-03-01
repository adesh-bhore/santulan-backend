"""Dashboard Service

Service for aggregating dashboard metrics and statistics.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.models.base_models import Depot, Vehicle, Driver, Route, Timetable
from app.models.plan_models import Plan, PlanVehicleAssignment, PlanDriverAssignment


class DashboardService:
    """Service for dashboard data aggregation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get complete dashboard summary with all metrics"""
        
        # Get active plans across all depots
        active_plans = self.db.query(Plan).filter(Plan.status == "ACTIVE").all()
        
        # Get all depots with their resources
        depots = self.db.query(Depot).all()
        depot_stats = []
        
        total_vehicles = 0
        total_drivers = 0
        total_trips_covered = 0
        total_trips_total = 0
        
        for depot in depots:
            # Count vehicles and drivers for this depot
            vehicle_count = self.db.query(func.count(Vehicle.vehicle_id)).filter(
                Vehicle.depot_id == depot.depot_id
            ).scalar() or 0
            
            driver_count = self.db.query(func.count(Driver.driver_id)).filter(
                Driver.depot_id == depot.depot_id
            ).scalar() or 0
            
            # Get active plan for this depot
            active_plan = next((p for p in active_plans if p.depot_id == depot.depot_id), None)
            
            # Calculate metrics for this depot
            vehicles_active = active_plan.fleet_size if active_plan else 0
            drivers_on_duty = int(driver_count * 0.7)  # Estimate 70% on duty
            trips_covered = active_plan.trips_covered if active_plan else 0
            trips_total = active_plan.trips_total if active_plan else 0
            fuel_level = 78  # Mock - would come from fuel tracking system
            
            depot_stats.append({
                "depot_id": depot.depot_id,
                "depot_name": depot.depot_name,
                "location": f"{depot.latitude}, {depot.longitude}",  # Format lat/long as location string
                "vehicles_total": vehicle_count,
                "vehicles_active": vehicles_active,
                "drivers_total": driver_count,
                "drivers_on_duty": drivers_on_duty,
                "trips_covered": trips_covered,
                "trips_total": trips_total,
                "fuel_level": fuel_level,
                "status": "operational" if fuel_level > 30 else "warning",
                "active_plan": {
                    "plan_id": str(active_plan.plan_id) if active_plan else None,
                    "version": active_plan.version if active_plan else None,
                    "fleet_size": active_plan.fleet_size if active_plan else 0,
                } if active_plan else None
            })
            
            total_vehicles += vehicle_count
            total_drivers += driver_count
            if active_plan:
                total_trips_covered += active_plan.trips_covered
                total_trips_total += active_plan.trips_total
        
        # Calculate aggregate metrics
        vehicles_active = sum(p.fleet_size for p in active_plans)
        drivers_on_duty = int(total_drivers * 0.7)
        
        # Calculate fleet utilization
        fleet_util = (vehicles_active / total_vehicles * 100) if total_vehicles > 0 else 0
        
        # Calculate on-time performance (mock for now)
        on_time_performance = 94.2
        
        # Fleet overview metrics
        fleet_metrics = [
            {
                "id": "buses-active",
                "value": vehicles_active,
                "total": total_vehicles,
                "label": "BUSES ACTIVE",
                "sublabel": f"of {total_vehicles} total",
                "gaugePercent": int((vehicles_active / total_vehicles * 100) if total_vehicles > 0 else 0),
                "trend": {"direction": "up", "value": "+3"}
            },
            {
                "id": "drivers-duty",
                "value": drivers_on_duty,
                "total": total_drivers,
                "label": "DRIVERS DUTY",
                "sublabel": f"of {total_drivers} total",
                "gaugePercent": int((drivers_on_duty / total_drivers * 100) if total_drivers > 0 else 0),
                "trend": {"direction": "down", "value": "-2"}
            },
            {
                "id": "trips-covered",
                "value": total_trips_covered,
                "total": total_trips_total,
                "label": "TRIPS COVERED",
                "sublabel": f"of {total_trips_total} total",
                "gaugePercent": int((total_trips_covered / total_trips_total * 100) if total_trips_total > 0 else 100),
                "trend": {"direction": "stable", "value": "0"}
            }
        ]
        
        # Status breakdown (mock - would come from real-time tracking)
        status_breakdown = [
            {"icon": "⦿", "label": "On Route", "count": vehicles_active - 5, "status": "active"},
            {"icon": "⏸", "label": "At Depot", "count": 5, "status": "idle"},
            {"icon": "⚙", "label": "Workshop", "count": total_vehicles - vehicles_active, "status": "maintenance"},
            {"icon": "⏰", "label": "On Schedule", "count": int(vehicles_active * 0.93), "status": "active"},
            {"icon": "⚠️", "label": "Delayed", "count": int(vehicles_active * 0.07), "status": "delayed"},
            {"icon": "🔴", "label": "Breakdown", "count": 0, "status": "active"}
        ]
        
        # Today's summary (mock - would come from real-time tracking)
        todays_summary = {
            "trips_completed": int(total_trips_covered * 0.64),  # Assume 64% of day complete
            "trips_total": total_trips_total,
            "on_time_percent": int(on_time_performance),
            "fuel_consumed": str(int(vehicles_active * 150 * 0.64)),  # 150L per vehicle per day
            "revenue": "42.3",  # Mock
            "breakdowns": 0,
            "delayed_buses": int(vehicles_active * 0.07)
        }
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "vehicles_active": vehicles_active,
                "vehicles_total": total_vehicles,
                "drivers_on_duty": drivers_on_duty,
                "drivers_total": total_drivers,
                "trips_covered": total_trips_covered,
                "trips_total": total_trips_total,
                "fleet_utilization": round(fleet_util, 1),
                "on_time_performance": on_time_performance
            },
            "fleet_metrics": fleet_metrics,
            "status_breakdown": status_breakdown,
            "todays_summary": todays_summary,
            "depots": depot_stats,
            "active_plans_count": len(active_plans)
        }
    
    def get_gauge_data(self) -> Dict[str, Any]:
        """Get data for the four cardinal gauges"""
        
        # Get totals
        total_vehicles = self.db.query(func.count(Vehicle.vehicle_id)).scalar() or 0
        total_drivers = self.db.query(func.count(Driver.driver_id)).scalar() or 0
        
        # Get active plans
        active_plans = self.db.query(Plan).filter(Plan.status == "ACTIVE").all()
        
        # Calculate active vehicles (sum of fleet_size from active plans)
        vehicles_active = sum(p.fleet_size for p in active_plans)
        
        # Estimate drivers on duty (70% of total)
        drivers_on_duty = int(total_drivers * 0.7)
        
        # Calculate trips
        total_trips_covered = sum(p.trips_covered for p in active_plans)
        total_trips_total = sum(p.trips_total for p in active_plans)
        
        # Mock previous values (would come from historical data)
        vehicles_previous = max(0, vehicles_active - 3)
        drivers_previous = drivers_on_duty + 2
        trips_previous = max(0, total_trips_covered - 2)
        
        # On-time performance (mock - would come from real-time tracking)
        on_time_current = 94.2
        on_time_previous = 93.8
        
        return {
            "success": True,
            "gauges": {
                "north": {
                    "label": "FLEET IN SERVICE",
                    "unit": "VEHICLES",
                    "value": vehicles_active,
                    "maxValue": total_vehicles,
                    "previousValue": vehicles_previous,
                    "trend": {
                        "direction": "up" if vehicles_active > vehicles_previous else "down" if vehicles_active < vehicles_previous else "stable",
                        "change": abs(vehicles_active - vehicles_previous)
                    }
                },
                "east": {
                    "label": "DRIVERS ON DUTY",
                    "unit": "DRIVERS",
                    "value": drivers_on_duty,
                    "maxValue": total_drivers,
                    "previousValue": drivers_previous,
                    "trend": {
                        "direction": "down" if drivers_on_duty < drivers_previous else "up" if drivers_on_duty > drivers_previous else "stable",
                        "change": abs(drivers_on_duty - drivers_previous)
                    }
                },
                "south": {
                    "label": "TRIPS COVERED",
                    "unit": "TRIPS",
                    "value": total_trips_covered,
                    "maxValue": total_trips_total,
                    "previousValue": trips_previous,
                    "trend": {
                        "direction": "up" if total_trips_covered > trips_previous else "down" if total_trips_covered < trips_previous else "stable",
                        "change": abs(total_trips_covered - trips_previous)
                    }
                },
                "west": {
                    "label": "ON-TIME PERFORMANCE",
                    "unit": "PERCENT",
                    "value": on_time_current,
                    "maxValue": 100,
                    "previousValue": on_time_previous,
                    "trend": {
                        "direction": "up" if on_time_current > on_time_previous else "down" if on_time_current < on_time_previous else "stable",
                        "change": round(abs(on_time_current - on_time_previous), 1)
                    }
                }
            }
        }
    
    def get_depot_list(self) -> Dict[str, Any]:
        """Get list of all depots with their resource counts"""
        
        depots = self.db.query(Depot).all()
        depot_list = []
        
        for depot in depots:
            # Count vehicles
            vehicle_count = self.db.query(func.count(Vehicle.vehicle_id)).filter(
                Vehicle.depot_id == depot.depot_id
            ).scalar() or 0
            
            # Count drivers
            driver_count = self.db.query(func.count(Driver.driver_id)).filter(
                Driver.depot_id == depot.depot_id
            ).scalar() or 0
            
            # Get active plan
            active_plan = self.db.query(Plan).filter(
                and_(
                    Plan.depot_id == depot.depot_id,
                    Plan.status == "ACTIVE"
                )
            ).first()
            
            depot_list.append({
                "depot_id": depot.depot_id,
                "depot_name": depot.depot_name,
                "location": f"{depot.latitude}, {depot.longitude}",  # Format lat/long as location string
                "vehicles": vehicle_count,
                "drivers": driver_count,
                "has_active_plan": active_plan is not None,
                "active_plan_version": active_plan.version if active_plan else None
            })
        
        return {
            "success": True,
            "depots": depot_list,
            "total": len(depot_list)
        }
