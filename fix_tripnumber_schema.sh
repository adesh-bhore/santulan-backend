#!/bin/bash

# Quick fix for tripNumber schema validation error
# Changes tripNumber from "U2" string to integer (1002)

echo "🔧 Fixing tripNumber Schema Validation Error"
echo "=================================================="

cd /var/www/santulan-backend/santulan-backend

echo "📝 Changes:"
echo "  - tripNumber: 'U2' → 1002 (integer)"
echo "  - Added is_unscheduled flag to identify surge trips"
echo "  - Added surge_reason field for trip description"
echo ""

# Restart backend service
echo "🔄 Restarting backend service..."
sudo systemctl restart santulan-backend

if [ $? -ne 0 ]; then
    echo "❌ Service restart failed!"
    exit 1
fi

echo "✅ Service restarted successfully"

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 3

# Check service status
echo "🔍 Checking service status..."
sudo systemctl status santulan-backend --no-pager | head -n 10

echo ""
echo "=================================================="
echo "✅ Fix applied!"
echo ""
echo "📋 Trip numbering scheme:"
echo "  - Regular trips: 1, 2, 3, ..."
echo "  - Unscheduled trips: 1001, 1002, 1003, ..."
echo ""
echo "🧪 Test now:"
echo "  Login as SURGE_DRV_SWGT_001 in Driver App"
echo "  Should see trip #1002 (unscheduled trip ID 2)"
echo ""
