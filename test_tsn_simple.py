"""Simple TSN Builder Test - Just one depot"""

import sys
sys.path.insert(0, '.')

from app.database.db import SessionLocal
from app.services.tsn_builder import TSNBuilder

def test_one_depot():
    """Test TSN building for just one depot"""
    db = SessionLocal()
    
    try:
        builder = TSNBuilder(db)
        
        print("Building TSN for DEPOT_BHSR (smallest depot with 4 routes)...")
        tsn = builder.build("DEPOT_BHSR", day_type="weekday")
        
        print(f"\n✓ Success!")
        print(f"  Nodes: {tsn.node_count}")
        print(f"  Edges: {tsn.edge_count}")
        
        # Show edge type breakdown
        edge_types = {}
        for edge in tsn.edges:
            edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
        
        print(f"\n  Edge types:")
        for edge_type, count in sorted(edge_types.items()):
            print(f"    {edge_type}: {count}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_one_depot()
