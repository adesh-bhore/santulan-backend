#!/bin/bash

# Deployment script for surge driver duty fix
# This script:
# 1. Applies migration 007 (adds is_surge_driver and is_surge_vehicle columns)
# 2. Restarts the backend service

echo "🚀 Deploying Surge Driver Duty Fix"
echo "=================================================="

# Navigate to backend directory
cd /var/www/santulan-backend/santulan-backend

# Activate virtual environment
echo "📦 Activating virtual environment..."
source ./venv/bin/activate

# Apply migration
echo "🔄 Applying migration 007..."
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ Migration failed!"
    exit 1
fi

echo "✅ Migration applied successfully"

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
echo "✅ Deployment complete!"
echo ""
echo "📋 What changed:"
echo "  1. Added is_surge_driver and is_surge_vehicle columns"
echo "  2. Surge drivers now see ONLY unscheduled trips (surge trips)"
echo "  3. Regular drivers see regular trips + unscheduled trips (if any)"
echo ""
echo "🧪 Testing:"
echo "  1. Login as surge driver: SURGE_DRV_SWGT_001"
echo "  2. Should see unscheduled trip ID: 2"
echo "  3. Regular drivers should NOT see this trip"
echo ""
echo "📊 Verify surge resources:"
echo "  python3 upload_surge_resources.py"
echo ""
