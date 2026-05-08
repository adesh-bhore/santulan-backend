# Corridor Clustering Test Guide

## Overview

This guide explains how to test corridor-based clustering with 16 commuters and pings at different locations.

---

## Test Scenario

### Setup:
- **16 test commuters** (phone: 9000000001 to 9000000016)
- **10 pings** at Market Yard (intermediate stop on Route 1: Swargate → Katraj)
- **6 pings** at Pune Station (different route)

### Expected Result:
- ✅ **Surge created** at Market Yard (10 pings ≥ threshold of 10)
- ✅ **Route 1 included** in surge route_ids (corridor clustering working!)
- ✅ **No surge** at Pune Station (6 pings < threshold of 10)

---

## Prerequisites

### 1. route_stops Table Must Exist
```bash
cd backend
python add_route_stops_table.py
```

This creates the route_stops table and adds Market Yard as an intermediate stop on Route 1.

### 2. Backend Running
```bash
# Local
uvicorn app.main:app --reload

# Or check if running on server
sudo systemctl status santulan-backend
```

### 3. Database Accessible
Ensure your `.env` file has correct database credentials.

---

## Running the Tests

### Option 1: Full Test (Recommended)

**Comprehensive test with detailed output:**

```bash
cd backend
python test_corridor_clustering.py
```

**What it does:**
1. ✅ Checks if route_stops table exists
2. ✅ Creates 16 test commuters
3. ✅ Creates 10 pings at Market Yard
4. ✅ Creates 6 pings at Pune Station
5. ✅ Runs clustering job
6. ✅ Verifies surge created for Route 1
7. ✅ Offers cleanup option

**Expected Output:**
```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CORRIDOR CLUSTERING TEST                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

STEP 1: Creating 16 Test Commuters
================================================================================
  1. Test Commuter 1 (9000000001) - Created
  2. Test Commuter 2 (9000000002) - Created
  ...
  16. Test Commuter 16 (9000000016) - Created

✓ Total commuters ready: 16

STEP 2: Creating 10 Pings at Market Yard
================================================================================
Location: Market Yard (intermediate stop on Route 1: Swargate-Katraj)
Expected: Should cluster for Route 1

  1. Commuter 1 → Ping 123 → Stop: Market Yard
  2. Commuter 2 → Ping 124 → Stop: Market Yard
  ...
  10. Commuter 10 → Ping 132 → Stop: Market Yard

✓ Created 10 pings at Market Yard

STEP 3: Creating 6 Pings at Pune Station
================================================================================
Location: Pune Station (different route)
Expected: Should NOT create surge (below threshold of 10)

  1. Commuter 11 → Ping 133 → Stop: Pune Station
  ...
  6. Commuter 16 → Ping 138 → Stop: Pune Station

✓ Created 6 pings at Pune Station

STEP 5: Running Clustering Job
================================================================================
Clustering Result:
  Status: success
  Pending Pings Processed: 16
  Surges Detected: 1

STEP 6: Verifying Surge Events
================================================================================
Found 1 surge event(s):

  Surge ID: 1
  Stop: Market Yard (STOP_MRKT)
  Route IDs: ['1', '5', '33']
  Ping Count: 10
  Status: pending
  ✓ Market Yard surge detected!
  ✓ Route 1 (Swargate-Katraj) included in route_ids!

TEST RESULT
================================================================================
✅ TEST PASSED!
✅ Corridor clustering is working correctly!
✅ Market Yard pings clustered for Route 1 (Swargate-Katraj)
```

---

### Option 2: Quick Test

**Fast test with minimal output:**

```bash
cd backend
python quick_test_clustering.py
```

**What it does:**
- Uses single test commuter
- Creates 10 pings at Market Yard
- Creates 6 pings at Pune Station
- Runs clustering
- Shows results

**Expected Output:**
```
============================================================
QUICK CORRIDOR CLUSTERING TEST
============================================================

Using commuter: COMM_001

1. Creating 10 pings at Market Yard...
   Ping 1: 123 → Market Yard
   ...

2. Creating 6 pings at Pune Station...
   Ping 1: 133 → Pune Station
   ...

3. Running clustering job...
   Status: success
   Surges: 1

4. Surge Events:
   - Stop: STOP_MRKT, Routes: ['1', '5', '33'], Count: 10
     ✅ SUCCESS! Route 1 detected at Market Yard!
```

---

## Understanding the Test

### Test Locations

#### Market Yard (STOP_MRKT)
- **Coordinates**: 18.49816, 73.85514
- **Route 1 Position**: Stop 2 of 5 (intermediate stop)
- **Route Sequence**: 
  1. Swargate (STOP_SWGT)
  2. **Market Yard (STOP_MRKT)** ← Test location
  3. Dhankawadi (STOP_DHNK)
  4. Bibvewadi (STOP_BIBW)
  5. Katraj (STOP_KTRJ)

#### Pune Station (STOP_PNST)
- **Coordinates**: 18.52859, 73.87420
- **Different Routes**: Not on Route 1
- **Purpose**: Control group (should NOT create surge)

---

## What the Test Validates

### 1. route_stops Table Working ✅
```python
# Clustering checks route_stops table
routes = db.query(RouteStop.route_id).filter(
    RouteStop.stop_id == 'STOP_MRKT'
).all()

# Should find: Route 1, Route 5, Route 33
```

### 2. Corridor Clustering ✅
```python
# Market Yard is intermediate stop on Route 1
# Pings at Market Yard should cluster for Route 1
# Even though Route 1 goes Swargate → Katraj
```

### 3. Threshold Logic ✅
```python
# 10 pings at Market Yard → Surge created ✅
# 6 pings at Pune Station → No surge ✅
# Threshold = 10 (demo setting)
```

### 4. Unique Commuter Counting ✅
```python
# 16 different commuters
# Each commuter counted once
# Prevents spam from same commuter
```

---

## Troubleshooting

### Issue: "route_stops table does NOT exist"

**Solution:**
```bash
cd backend
python add_route_stops_table.py
```

### Issue: "No surge events found"

**Possible causes:**
1. Threshold too high (check config: `DRT_SURGE_PING_THRESHOLD`)
2. Pings not detected at stops (check coordinates)
3. Clustering job not running

**Check threshold:**
```python
# In backend/app/config.py
drt_surge_ping_threshold: int = 10  # Should be 10 for demo
```

### Issue: "Route 1 NOT in route_ids"

**Possible causes:**
1. route_stops table empty
2. Market Yard not in route_stops
3. Clustering logic not updated

**Verify route_stops:**
```sql
SELECT * FROM route_stops WHERE stop_id = 'STOP_MRKT';
-- Should return rows for Route 1, 5, 33
```

### Issue: "Surge created at Pune Station"

**This is unexpected!** Only 6 pings should not create surge.

**Check:**
1. Threshold setting (should be 10)
2. Duplicate pings from same commuter
3. Old pings not cleaned up

---

## Cleanup

### Option 1: During Test
The test script offers cleanup at the end:
```
Do you want to cleanup test data? (y/n): y
```

### Option 2: Manual Cleanup
```sql
-- Delete test pings
DELETE FROM commuter_pings WHERE commuter_id LIKE 'COMM_%';

-- Delete test surges
DELETE FROM surge_events WHERE status = 'pending';

-- Delete test commuters
DELETE FROM commuters WHERE phone LIKE '900000%';
```

### Option 3: Python Script
```python
from app.database.db import get_db
from app.drt.models import CommuterPing, SurgeEvent, Commuter

db = next(get_db())

# Delete test data
db.query(CommuterPing).filter(CommuterPing.commuter_id.like('COMM_%')).delete()
db.query(SurgeEvent).filter(SurgeEvent.status == 'pending').delete()
db.query(Commuter).filter(Commuter.phone.like('900000%')).delete()
db.commit()
```

---

## Test Data Summary

### Commuters Created
| # | Phone | Name | Purpose |
|---|-------|------|---------|
| 1-10 | 9000000001-10 | Test Commuter 1-10 | Market Yard pings |
| 11-16 | 9000000011-16 | Test Commuter 11-16 | Pune Station pings |

### Pings Created
| Location | Count | Commuters | Expected Result |
|----------|-------|-----------|-----------------|
| Market Yard | 10 | 1-10 | Surge for Route 1 ✅ |
| Pune Station | 6 | 11-16 | No surge ✅ |

### Expected Surge
```json
{
  "surge_id": 1,
  "stop_id": "STOP_MRKT",
  "stop_name": "Market Yard",
  "route_ids": ["1", "5", "33"],
  "ping_count": 10,
  "status": "pending"
}
```

---

## Success Criteria

✅ **Test passes if:**
1. 16 commuters created successfully
2. 10 pings created at Market Yard
3. 6 pings created at Pune Station
4. Clustering job runs successfully
5. 1 surge created at Market Yard
6. Route 1 included in surge route_ids
7. No surge at Pune Station

❌ **Test fails if:**
1. route_stops table doesn't exist
2. No surge created at Market Yard
3. Route 1 NOT in surge route_ids
4. Surge created at Pune Station (unexpected)

---

## Next Steps After Test

### If Test Passes ✅
1. Corridor clustering is working!
2. Add more route stop data for other routes
3. Test with real commuter app
4. Deploy to production

### If Test Fails ❌
1. Check route_stops table exists
2. Verify Market Yard in route_stops
3. Check clustering logic updated
4. Review logs for errors
5. Verify threshold setting

---

## Files

- `test_corridor_clustering.py` - Full comprehensive test
- `quick_test_clustering.py` - Quick simple test
- `add_route_stops_table.py` - Setup route_stops table
- `TEST_CORRIDOR_CLUSTERING.md` - This guide

---

## Summary

This test validates that corridor-based clustering works correctly by:
- Creating pings at intermediate stops (not just start/end)
- Verifying those pings cluster for the correct route
- Ensuring threshold logic works properly
- Testing with multiple commuters

**Run the test to verify your corridor clustering implementation!** 🚀

