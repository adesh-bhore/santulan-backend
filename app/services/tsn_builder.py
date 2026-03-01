"""Time-Space Network (TSN) Builder Service

Constructs in-memory graph representation of vehicle/driver scheduling problem.
Each depot builds its own independent TSN with no cross-depot edges.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Literal, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import math

from app.models.base_models import Depot, Route, Stop, Vehicle, Driver, Timetable


@dataclass
class TSNNode:
    """Node in Time-Space Network representing (location, time) pair"""
    location_id: str  # stop_id or depot_id
    time: datetime
    node_type: Literal["stop", "depot"]
    node_id: str = field(init=False)
    
    def __post_init__(self):
        # Create unique node ID
        time_str = self.time.strftime("%H:%M:%S")
        self.node_id = f"{self.location_id}_{time_str}"
    
    def __hash__(self):
        return hash(self.node_id)
    
    def __eq__(self, other):
        if not isinstance(other, TSNNode):
            return False
        return self.node_id == other.node_id


@dataclass
class TSNEdge:
    """Edge in Time-Space Network representing possible vehicle/driver movement"""
    from_node: TSNNode
    to_node: TSNNode
    edge_type: Literal["trip", "wait", "depot_start", "depot_end", "deadhead"]
    cost: float  # distance in km or time in minutes
    metadata: Dict = field(default_factory=dict)
    edge_id: str = field(init=False)
    
    def __post_init__(self):
        self.edge_id = f"{self.from_node.node_id}_to_{self.to_node.node_id}_{self.edge_type}"
    
    def __hash__(self):
        return hash(self.edge_id)
    
    def __eq__(self, other):
        if not isinstance(other, TSNEdge):
            return False
        return self.edge_id == other.edge_id


@dataclass
class TSNGraph:
    """Complete Time-Space Network for a depot"""
    depot_id: str
    day_type: str
    nodes: List[TSNNode] = field(default_factory=list)
    edges: List[TSNEdge] = field(default_factory=list)
    _node_map: Dict[str, TSNNode] = field(default_factory=dict, repr=False)
    _outgoing_edges: Dict[str, List[TSNEdge]] = field(default_factory=dict, repr=False)
    _incoming_edges: Dict[str, List[TSNEdge]] = field(default_factory=dict, repr=False)
    
    def add_node(self, node: TSNNode):
        """Add node to graph"""
        if node.node_id not in self._node_map:
            self.nodes.append(node)
            self._node_map[node.node_id] = node
            self._outgoing_edges[node.node_id] = []
            self._incoming_edges[node.node_id] = []
    
    def add_edge(self, edge: TSNEdge):
        """Add edge to graph"""
        # Ensure nodes exist
        self.add_node(edge.from_node)
        self.add_node(edge.to_node)
        
        # Add edge
        self.edges.append(edge)
        self._outgoing_edges[edge.from_node.node_id].append(edge)
        self._incoming_edges[edge.to_node.node_id].append(edge)
    
    def get_outgoing_edges(self, node: TSNNode) -> List[TSNEdge]:
        """Get all edges leaving this node"""
        return self._outgoing_edges.get(node.node_id, [])
    
    def get_incoming_edges(self, node: TSNNode) -> List[TSNEdge]:
        """Get all edges entering this node"""
        return self._incoming_edges.get(node.node_id, [])
    
    def get_node(self, node_id: str) -> Optional[TSNNode]:
        """Get node by ID"""
        return self._node_map.get(node_id)
    
    @property
    def node_count(self) -> int:
        return len(self.nodes)
    
    @property
    def edge_count(self) -> int:
        return len(self.edges)


class TSNBuilder:
    """Builds Time-Space Network for depot-specific optimization"""
    
    def __init__(self, db: Session):
        self.db = db
        self.max_wait_minutes = 180  # 3 hours max wait time
        self.max_deadhead_km = 15.0  # 15 km max deadhead distance
        self.depot_time_interval_minutes = 5  # Depot nodes every 5 minutes
    
    @staticmethod
    def _time_diff_minutes(end_time, start_time) -> float:
        """Calculate difference between two time objects in minutes"""
        # Convert time objects to datetime on same day for subtraction
        base_date = datetime(2000, 1, 1)
        start_dt = datetime.combine(base_date, start_time)
        end_dt = datetime.combine(base_date, end_time)
        
        # Handle overnight trips (end time < start time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        return (end_dt - start_dt).total_seconds() / 60
    
    def build(self, depot_id: str, day_type: str = "weekday") -> TSNGraph:
        """
        Build Time-Space Network for specific depot and day type.
        
        Args:
            depot_id: Depot identifier
            day_type: "weekday" or "weekend"
        
        Returns:
            TSNGraph with nodes and edges for this depot only
        """
        print(f"Building TSN for {depot_id} ({day_type})...")
        
        # Initialize graph
        tsn = TSNGraph(depot_id=depot_id, day_type=day_type)
        
        # Step 1: Load depot-specific data
        depot_data = self._load_depot_data(depot_id, day_type)
        
        if not depot_data['trips']:
            raise ValueError(f"No trips found for depot {depot_id} on {day_type}")
        
        print(f"  Loaded: {len(depot_data['routes'])} routes, "
              f"{len(depot_data['trips'])} trips, "
              f"{len(depot_data['vehicles'])} vehicles, "
              f"{len(depot_data['drivers'])} drivers")
        
        # Step 2: Create trip nodes and edges
        self._create_trip_nodes_and_edges(tsn, depot_data)
        print(f"  Created trip nodes: {tsn.node_count} nodes, {tsn.edge_count} edges")
        
        # Step 3: Create depot nodes
        self._create_depot_nodes(tsn, depot_data)
        print(f"  Added depot nodes: {tsn.node_count} nodes")
        
        # Step 4: Create wait edges
        self._create_wait_edges(tsn)
        print(f"  Added wait edges: {tsn.edge_count} edges")
        
        # Step 5: Create deadhead edges
        self._create_deadhead_edges(tsn, depot_data)
        print(f"  Added deadhead edges: {tsn.edge_count} edges")
        
        # Step 6: Create depot start/end edges
        self._create_depot_boundary_edges(tsn, depot_data)
        print(f"  Added depot boundary edges: {tsn.edge_count} edges")
        
        print(f"✓ TSN built: {tsn.node_count} nodes, {tsn.edge_count} edges")
        
        return tsn
    
    def _load_depot_data(self, depot_id: str, day_type: str) -> Dict:
        """Load all data for specific depot"""
        
        # Get depot info
        depot = self.db.query(Depot).filter(Depot.depot_id == depot_id).first()
        if not depot:
            raise ValueError(f"Depot {depot_id} not found")
        
        # Get depot's routes
        routes = self.db.query(Route).filter(Route.depot_id == depot_id).all()
        route_ids = [r.route_id for r in routes]
        
        if not route_ids:
            raise ValueError(f"No routes found for depot {depot_id}")
        
        # Get depot's trips
        trips = self.db.query(Timetable).filter(
            and_(
                Timetable.route_id.in_(route_ids),
                Timetable.day_type == day_type
            )
        ).order_by(Timetable.start_time).all()
        
        # Get depot's vehicles
        vehicles = self.db.query(Vehicle).filter(Vehicle.depot_id == depot_id).all()
        
        # Get depot's drivers
        drivers = self.db.query(Driver).filter(Driver.depot_id == depot_id).all()
        
        # Get all stops used by depot's routes
        stop_ids = set()
        for trip in trips:
            stop_ids.add(trip.start_stop_id)
            stop_ids.add(trip.end_stop_id)
        
        stops = self.db.query(Stop).filter(Stop.stop_id.in_(stop_ids)).all()
        stops_dict = {s.stop_id: s for s in stops}
        
        return {
            'depot': depot,
            'routes': routes,
            'trips': trips,
            'vehicles': vehicles,
            'drivers': drivers,
            'stops': stops_dict
        }
    
    def _create_trip_nodes_and_edges(self, tsn: TSNGraph, depot_data: Dict):
        """Create nodes for trip starts/ends and edges for scheduled trips"""
        
        # Base date for converting time objects to datetime
        base_date = datetime(2000, 1, 1)
        
        for trip in depot_data['trips']:
            # Convert time objects to datetime
            start_datetime = datetime.combine(base_date, trip.start_time)
            end_datetime = datetime.combine(base_date, trip.end_time)
            
            # Create start node
            start_node = TSNNode(
                location_id=trip.start_stop_id,
                time=start_datetime,
                node_type="stop"
            )
            tsn.add_node(start_node)
            
            # Create end node
            end_node = TSNNode(
                location_id=trip.end_stop_id,
                time=end_datetime,
                node_type="stop"
            )
            tsn.add_node(end_node)
            
            # Create trip edge (scheduled service, zero cost)
            trip_edge = TSNEdge(
                from_node=start_node,
                to_node=end_node,
                edge_type="trip",
                cost=0.0,  # Scheduled service has no penalty
                metadata={
                    'trip_id': trip.trip_id,
                    'route_id': trip.route_id,
                    'duration_minutes': self._time_diff_minutes(trip.end_time, trip.start_time)
                }
            )
            tsn.add_edge(trip_edge)
    
    def _create_depot_nodes(self, tsn: TSNGraph, depot_data: Dict):
        """Create depot nodes at regular intervals throughout the day"""
        
        depot = depot_data['depot']
        
        # Find time range from trips
        trips = depot_data['trips']
        if not trips:
            return
        
        min_time = min(trip.start_time for trip in trips)
        max_time = max(trip.end_time for trip in trips)
        
        # Convert time objects to datetime for arithmetic
        base_date = datetime(2000, 1, 1)
        min_datetime = datetime.combine(base_date, min_time)
        max_datetime = datetime.combine(base_date, max_time)
        
        # Add buffer before first trip and after last trip
        start_time = min_datetime - timedelta(hours=1)
        end_time = max_datetime + timedelta(hours=1)
        
        # Create depot nodes every N minutes
        current_time = start_time
        while current_time <= end_time:
            depot_node = TSNNode(
                location_id=depot.depot_id,
                time=current_time,
                node_type="depot"
            )
            tsn.add_node(depot_node)
            current_time += timedelta(minutes=self.depot_time_interval_minutes)
    
    def _create_wait_edges(self, tsn: TSNGraph):
        """Create wait edges at same location between compatible times"""
        
        # Group nodes by location
        nodes_by_location: Dict[str, List[TSNNode]] = {}
        for node in tsn.nodes:
            if node.location_id not in nodes_by_location:
                nodes_by_location[node.location_id] = []
            nodes_by_location[node.location_id].append(node)
        
        # For each location, create wait edges between consecutive times
        for location_id, location_nodes in nodes_by_location.items():
            # Sort by time
            sorted_nodes = sorted(location_nodes, key=lambda n: n.time)
            
            # Create wait edges
            for i in range(len(sorted_nodes) - 1):
                from_node = sorted_nodes[i]
                to_node = sorted_nodes[i + 1]
                
                # Calculate wait time
                wait_minutes = (to_node.time - from_node.time).total_seconds() / 60
                
                # Only create wait edge if within max wait time
                if wait_minutes <= self.max_wait_minutes:
                    wait_edge = TSNEdge(
                        from_node=from_node,
                        to_node=to_node,
                        edge_type="wait",
                        cost=0.0,  # Waiting has no cost (necessary between trips)
                        metadata={'wait_minutes': wait_minutes}
                    )
                    tsn.add_edge(wait_edge)
    
    def _create_deadhead_edges(self, tsn: TSNGraph, depot_data: Dict):
        """Create deadhead edges for empty vehicle movement between stops"""
        
        stops = depot_data['stops']
        
        # Get all stop nodes (not depot nodes)
        stop_nodes = [n for n in tsn.nodes if n.node_type == "stop"]
        
        # Group stop nodes by time windows (to limit edge creation)
        time_windows: Dict[int, List[TSNNode]] = {}
        for node in stop_nodes:
            # Group by hour
            hour_key = node.time.hour
            if hour_key not in time_windows:
                time_windows[hour_key] = []
            time_windows[hour_key].append(node)
        
        # Create deadhead edges within time windows
        for hour_key, window_nodes in time_windows.items():
            for from_node in window_nodes:
                for to_node in window_nodes:
                    # Skip same location
                    if from_node.location_id == to_node.location_id:
                        continue
                    
                    # Only forward in time
                    if to_node.time <= from_node.time:
                        continue
                    
                    # Check if stops exist
                    if from_node.location_id not in stops or to_node.location_id not in stops:
                        continue
                    
                    # Calculate distance
                    from_stop = stops[from_node.location_id]
                    to_stop = stops[to_node.location_id]
                    distance_km = self._calculate_distance(
                        from_stop.latitude, from_stop.longitude,
                        to_stop.latitude, to_stop.longitude
                    )
                    
                    # Only create edge if within max deadhead distance
                    if distance_km <= self.max_deadhead_km:
                        # Calculate time needed for deadhead
                        avg_speed_kmh = 30.0  # Average city speed
                        time_needed_minutes = (distance_km / avg_speed_kmh) * 60
                        time_available_minutes = (to_node.time - from_node.time).total_seconds() / 60
                        
                        # Only create edge if enough time
                        if time_needed_minutes <= time_available_minutes:
                            deadhead_edge = TSNEdge(
                                from_node=from_node,
                                to_node=to_node,
                                edge_type="deadhead",
                                cost=distance_km,  # Deadhead cost is distance
                                metadata={
                                    'distance_km': distance_km,
                                    'time_minutes': time_needed_minutes
                                }
                            )
                            tsn.add_edge(deadhead_edge)
    
    def _create_depot_boundary_edges(self, tsn: TSNGraph, depot_data: Dict):
        """Create edges from depot to first trips and from last trips to depot"""
        
        depot = depot_data['depot']
        stops = depot_data['stops']
        
        # Get depot nodes and stop nodes
        depot_nodes = [n for n in tsn.nodes if n.node_type == "depot"]
        stop_nodes = [n for n in tsn.nodes if n.node_type == "stop"]
        
        # Create depot_start edges (depot → trip starts)
        for depot_node in depot_nodes:
            for stop_node in stop_nodes:
                # Only forward in time
                if stop_node.time <= depot_node.time:
                    continue
                
                # Check if stop exists
                if stop_node.location_id not in stops:
                    continue
                
                # Calculate distance from depot to stop
                stop = stops[stop_node.location_id]
                distance_km = self._calculate_distance(
                    depot.latitude, depot.longitude,
                    stop.latitude, stop.longitude
                )
                
                # Calculate time needed
                avg_speed_kmh = 30.0
                time_needed_minutes = (distance_km / avg_speed_kmh) * 60
                time_available_minutes = (stop_node.time - depot_node.time).total_seconds() / 60
                
                # Only create edge if enough time and within reasonable distance
                if time_needed_minutes <= time_available_minutes and distance_km <= self.max_deadhead_km:
                    depot_start_edge = TSNEdge(
                        from_node=depot_node,
                        to_node=stop_node,
                        edge_type="depot_start",
                        cost=distance_km,
                        metadata={
                            'distance_km': distance_km,
                            'time_minutes': time_needed_minutes
                        }
                    )
                    tsn.add_edge(depot_start_edge)
        
        # Create depot_end edges (trip ends → depot)
        for stop_node in stop_nodes:
            for depot_node in depot_nodes:
                # Only forward in time
                if depot_node.time <= stop_node.time:
                    continue
                
                # Check if stop exists
                if stop_node.location_id not in stops:
                    continue
                
                # Calculate distance from stop to depot
                stop = stops[stop_node.location_id]
                distance_km = self._calculate_distance(
                    stop.latitude, stop.longitude,
                    depot.latitude, depot.longitude
                )
                
                # Calculate time needed
                avg_speed_kmh = 30.0
                time_needed_minutes = (distance_km / avg_speed_kmh) * 60
                time_available_minutes = (depot_node.time - stop_node.time).total_seconds() / 60
                
                # Only create edge if enough time and within reasonable distance
                if time_needed_minutes <= time_available_minutes and distance_km <= self.max_deadhead_km:
                    depot_end_edge = TSNEdge(
                        from_node=stop_node,
                        to_node=depot_node,
                        edge_type="depot_end",
                        cost=distance_km,
                        metadata={
                            'distance_km': distance_km,
                            'time_minutes': time_needed_minutes
                        }
                    )
                    tsn.add_edge(depot_end_edge)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate Haversine distance between two coordinates in km"""
        
        # Earth radius in km
        R = 6371.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
