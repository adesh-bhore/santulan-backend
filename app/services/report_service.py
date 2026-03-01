"""Report Service

Service for generating various types of reports.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid

from app.models.base_models import Depot, Vehicle, Driver, Route, Stop, Timetable
from app.models.plan_models import Plan, PlanVehicleAssignment, PlanDriverAssignment
from app.schemas.report_schemas import (
    ReportType, ReportFormat, ReportRequest, 
    ReportResponse, ReportFile, ReportListItem
)


class ReportService:
    """Service for generating reports"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_report(self, request: ReportRequest) -> ReportResponse:
        """Generate a report based on request parameters"""
        
        # Generate unique report ID
        report_id = f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # Collect report data based on type
        if request.report_type == ReportType.DAILY_OPERATIONS:
            data = self._get_daily_operations_data(
                request.start_date, request.end_date, request.depot_id
            )
        elif request.report_type == ReportType.MONTHLY_FLEET:
            data = self._get_monthly_fleet_data(
                request.start_date, request.end_date, request.depot_id
            )
        elif request.report_type == ReportType.DRIVER_DUTY:
            data = self._get_driver_duty_data(
                request.start_date, request.end_date, request.depot_id
            )
        elif request.report_type == ReportType.ROUTE_PERFORMANCE:
            data = self._get_route_performance_data(
                request.start_date, request.end_date, request.depot_id
            )
        elif request.report_type == ReportType.FUEL_CONSUMPTION:
            data = self._get_fuel_consumption_data(
                request.start_date, request.end_date, request.depot_id
            )
        elif request.report_type == ReportType.PLAN_HISTORY:
            data = self._get_plan_history_data(
                request.start_date, request.end_date, request.depot_id
            )
        else:
            raise ValueError(f"Unknown report type: {request.report_type}")
        
        # Generate files (in production, this would create actual PDF/Excel files)
        files = self._generate_report_files(
            report_id, request.report_type, request.format, data
        )
        
        return ReportResponse(
            success=True,
            report_id=report_id,
            report_type=request.report_type.value,
            generated_at=datetime.now().isoformat(),
            files=files
        )
    
    def _get_daily_operations_data(
        self, start_date: date, end_date: date, depot_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get data for daily operations report"""
        
        # Query plans in date range
        query = self.db.query(Plan).filter(
            and_(
                Plan.created_at >= start_date,
                Plan.created_at <= end_date
            )
        )
        
        if depot_id:
            query = query.filter(Plan.depot_id == depot_id)
        
        plans = query.all()
        
        # Aggregate statistics
        total_plans = len(plans)
        active_plans = sum(1 for p in plans if p.status == "ACTIVE")
        total_vehicles_used = sum(p.fleet_size for p in plans)
        
        return {
            "total_plans": total_plans,
            "active_plans": active_plans,
            "total_vehicles_used": total_vehicles_used,
            "plans": [
                {
                    "plan_id": str(p.plan_id),
                    "depot_id": p.depot_id,
                    "created_at": p.created_at.isoformat(),
                    "fleet_size": p.fleet_size,
                    "status": p.status
                }
                for p in plans
            ]
        }
    
    def _get_monthly_fleet_data(
        self, start_date: date, end_date: date, depot_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get data for monthly fleet report"""
        
        # Query vehicles
        query = self.db.query(Vehicle)
        if depot_id:
            query = query.filter(Vehicle.depot_id == depot_id)
        
        vehicles = query.all()
        
        # Calculate fleet statistics
        total_vehicles = len(vehicles)
        by_type = {}
        by_depot = {}
        
        for v in vehicles:
            # Count by type
            if v.vehicle_type not in by_type:
                by_type[v.vehicle_type] = 0
            by_type[v.vehicle_type] += 1
            
            # Count by depot
            if v.depot_id not in by_depot:
                by_depot[v.depot_id] = 0
            by_depot[v.depot_id] += 1
        
        return {
            "total_vehicles": total_vehicles,
            "by_type": by_type,
            "by_depot": by_depot,
            "vehicles": [
                {
                    "vehicle_id": v.vehicle_id,
                    "vehicle_number": v.vehicle_number,
                    "vehicle_type": v.vehicle_type,
                    "depot_id": v.depot_id,
                    "capacity": v.capacity
                }
                for v in vehicles
            ]
        }
    
    def _get_driver_duty_data(
        self, start_date: date, end_date: date, depot_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get data for driver duty report"""
        
        # Query drivers
        query = self.db.query(Driver)
        if depot_id:
            query = query.filter(Driver.depot_id == depot_id)
        
        drivers = query.all()
        
        # Calculate driver statistics
        total_drivers = len(drivers)
        by_shift = {}
        by_depot = {}
        
        for d in drivers:
            # Count by shift
            if d.shift_type not in by_shift:
                by_shift[d.shift_type] = 0
            by_shift[d.shift_type] += 1
            
            # Count by depot
            if d.depot_id not in by_depot:
                by_depot[d.depot_id] = 0
            by_depot[d.depot_id] += 1
        
        return {
            "total_drivers": total_drivers,
            "by_shift": by_shift,
            "by_depot": by_depot,
            "drivers": [
                {
                    "driver_id": d.driver_id,
                    "driver_name": d.driver_name,
                    "shift_type": d.shift_type,
                    "depot_id": d.depot_id,
                    "max_hours": d.max_hours
                }
                for d in drivers
            ]
        }
    
    def _get_route_performance_data(
        self, start_date: date, end_date: date, depot_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get data for route performance report"""
        
        # Query routes
        query = self.db.query(Route)
        if depot_id:
            query = query.filter(Route.depot_id == depot_id)
        
        routes = query.all()
        
        # Calculate route statistics
        total_routes = len(routes)
        by_depot = {}
        
        for r in routes:
            if r.depot_id not in by_depot:
                by_depot[r.depot_id] = 0
            by_depot[r.depot_id] += 1
        
        return {
            "total_routes": total_routes,
            "by_depot": by_depot,
            "routes": [
                {
                    "route_id": r.route_id,
                    "route_number": r.route_number,
                    "route_name": r.route_name,
                    "depot_id": r.depot_id
                }
                for r in routes
            ]
        }
    
    def _get_fuel_consumption_data(
        self, start_date: date, end_date: date, depot_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get data for fuel consumption report"""
        
        # Query vehicles with fuel data
        query = self.db.query(Vehicle)
        if depot_id:
            query = query.filter(Vehicle.depot_id == depot_id)
        
        vehicles = query.all()
        
        # Calculate fuel statistics (mock data for now)
        total_vehicles = len(vehicles)
        estimated_fuel_per_vehicle = 150  # liters per day
        days = (end_date - start_date).days + 1
        
        total_fuel = total_vehicles * estimated_fuel_per_vehicle * days
        
        return {
            "total_vehicles": total_vehicles,
            "days": days,
            "estimated_fuel_per_vehicle_per_day": estimated_fuel_per_vehicle,
            "total_estimated_fuel": total_fuel,
            "vehicles": [
                {
                    "vehicle_id": v.vehicle_id,
                    "vehicle_number": v.vehicle_number,
                    "estimated_daily_fuel": estimated_fuel_per_vehicle
                }
                for v in vehicles
            ]
        }
    
    def _get_plan_history_data(
        self, start_date: date, end_date: date, depot_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get data for plan history report"""
        
        # Query plans in date range
        query = self.db.query(Plan).filter(
            and_(
                Plan.created_at >= start_date,
                Plan.created_at <= end_date
            )
        )
        
        if depot_id:
            query = query.filter(Plan.depot_id == depot_id)
        
        plans = query.order_by(Plan.created_at.desc()).all()
        
        return {
            "total_plans": len(plans),
            "plans": [
                {
                    "plan_id": str(p.plan_id),
                    "depot_id": p.depot_id,
                    "created_at": p.created_at.isoformat(),
                    "fleet_size": p.fleet_size,
                    "trips_covered": p.trips_covered,
                    "trips_total": p.trips_total,
                    "status": p.status,
                    "version": p.version
                }
                for p in plans
            ]
        }
    
    def _generate_report_files(
        self, report_id: str, report_type: ReportType, 
        format: ReportFormat, data: Dict[str, Any]
    ) -> List[ReportFile]:
        """Generate report files (mock implementation)"""
        
        files = []
        base_filename = f"{report_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # In production, this would generate actual PDF/Excel files
        # For now, we return mock file information
        
        if format in [ReportFormat.PDF, ReportFormat.BOTH]:
            files.append(ReportFile(
                filename=f"{base_filename}.pdf",
                format="pdf",
                size_bytes=524288,  # Mock size
                download_url=f"/api/reports/download/{report_id}.pdf"
            ))
        
        if format in [ReportFormat.EXCEL, ReportFormat.BOTH]:
            files.append(ReportFile(
                filename=f"{base_filename}.xlsx",
                format="excel",
                size_bytes=262144,  # Mock size
                download_url=f"/api/reports/download/{report_id}.xlsx"
            ))
        
        return files
    
    def list_reports(
        self, limit: int = 20, offset: int = 0, depot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """List recent reports (mock implementation)"""
        
        # In production, this would query a reports table
        # For now, return mock data
        
        mock_reports = [
            ReportListItem(
                report_id=f"RPT_20240225_{i:03d}",
                report_type="daily_operations",
                report_name="Daily Operations Report",
                generated_at=datetime.now().isoformat(),
                start_date="2024-02-01",
                end_date="2024-02-28",
                depot_id=depot_id,
                files=[
                    ReportFile(
                        filename=f"daily_operations_20240225_{i:03d}.pdf",
                        format="pdf",
                        size_bytes=524288,
                        download_url=f"/api/reports/download/RPT_20240225_{i:03d}.pdf"
                    )
                ]
            )
            for i in range(5)
        ]
        
        return {
            "success": True,
            "reports": mock_reports[offset:offset+limit],
            "total": len(mock_reports),
            "limit": limit,
            "offset": offset
        }
