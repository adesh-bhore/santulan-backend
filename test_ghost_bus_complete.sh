#!/bin/bash

# Complete Ghost Bus Suppression Testing Script
# Runs all tests in sequence

echo "🚀 Ghost Bus Suppression - Complete Testing"
echo "============================================================"
echo ""

cd /var/www/santulan-backend/santulan-backend
source ./venv/bin/activate

# Step 1: Verify Phase 3 installation
echo "Step 1: Verifying Phase 3 Installation"
echo "------------------------------------------------------------"
python3 verify_phase3.py
if [ $? -ne 0 ]; then
    echo "❌ Phase 3 verification failed. Please fix errors before continuing."
    exit 1
fi
echo ""

# Step 2: Generate test data
echo "Step 2: Generating Test Passenger Count Data"
echo "------------------------------------------------------------"
python3 test_ghost_bus_data.py
if [ $? -ne 0 ]; then
    echo "❌ Test data generation failed."
    exit 1
fi
echo ""

# Step 3: Identify ghost buses
echo "Step 3: Identifying Low Demand Trips"
echo "------------------------------------------------------------"
python3 test_identify_ghost_buses.py
if [ $? -ne 0 ]; then
    echo "❌ Ghost bus identification failed."
    exit 1
fi
echo ""

# Step 4: Create suppression
echo "Step 4: Creating Suppression Recommendation"
echo "------------------------------------------------------------"
python3 test_create_suppression.py
if [ $? -ne 0 ]; then
    echo "❌ Suppression creation failed."
    exit 1
fi
echo ""

echo "============================================================"
echo "✅ All tests completed successfully!"
echo ""
echo "📋 Summary:"
echo "  ✅ Phase 3 verified"
echo "  ✅ Test data generated (30 days)"
echo "  ✅ Ghost buses identified"
echo "  ✅ Suppression recommendation created"
echo ""
echo "🧪 Next steps:"
echo "  1. Test API endpoints (see GHOST_BUS_TESTING_GUIDE.md)"
echo "  2. Test frontend integration"
echo "  3. Test approval/rejection flow"
echo ""
echo "📊 View pending suppressions:"
echo "  curl -X GET 'https://santulan.duckdns.org/api/drt/suppression/pending'"
echo ""
