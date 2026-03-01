"""Test script for TSN Builder

Run this after uploading CSV data to test TSN building.
"""

import sys
from app.database.db import SessionLocal
from app.services.tsn_builder import TSNBuilder
from app.models.base_models import Depot


def test_tsn_builder():
    """Test TSN building for all depots"""
    
    db = SessionLocal()
    
    try:
        # Get all depots
        depots = db.query(Depot).all()
        
        if not depots:
            print("❌ No depots found in database. Please upload CSV data first.")
            return
        
        print(f"Found {len(depots)} depots in database\n")
        print("=" * 70)
        
        # Build TSN for each depot
        builder = TSNBuilder(db)
        
        for depot in depots:
            print(f"\n🏢 Testing {depot.depot_name} ({depot.depot_id})")
            print("-" * 70)
            
            try:
                # Build TSN for weekday
                tsn = builder.build(depot.depot_id, day_type="weekday")
                
                print(f"✓ TSN built successfully!")
                print(f"  Nodes: {tsn.node_count:,}")
                print(f"  Edges: {tsn.edge_count:,}")
                
                # Count edge types
                edge_types = {}
                for edge in tsn.edges:
                    edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
                
                print(f"\n  Edge breakdown:")
                for edge_type, count in sorted(edge_types.items()):
                    print(f"    {edge_type:15s}: {count:,}")
                
                # Count node types
                node_types = {}
                for node in tsn.nodes:
                    node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
                
                print(f"\n  Node breakdown:")
                for node_type, count in sorted(node_types.items()):
                    print(f"    {node_type:15s}: {count:,}")
                
            except Exception as e:
                print(f"❌ Error building TSN: {str(e)}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 70)
        print("✓ TSN Builder test complete!")
        
    finally:
        db.close()


if __name__ == "__main__":
    print("TSN Builder Test")
    print("=" * 70)
    print("This script tests the TSN Builder service.")
    print("Make sure you have uploaded CSV data first!")
    print("=" * 70)
    print()
    
    test_tsn_builder()
