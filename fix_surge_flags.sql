-- Fix surge flags for surge drivers and vehicles
-- Run this to set is_surge_driver=true and is_surge_vehicle=true

-- Update surge drivers
UPDATE drivers 
SET is_surge_driver = true 
WHERE driver_id LIKE 'SURGE_DRV_%';

-- Update surge vehicles
UPDATE vehicles 
SET is_surge_vehicle = true 
WHERE vehicle_id LIKE 'SURGE_VEH_%';

-- Verify the changes
SELECT 'Surge Drivers:' as type, COUNT(*) as count 
FROM drivers 
WHERE is_surge_driver = true;

SELECT 'Surge Vehicles:' as type, COUNT(*) as count 
FROM vehicles 
WHERE is_surge_vehicle = true;

-- Show all surge drivers
SELECT driver_id, driver_name, depot_id, is_surge_driver 
FROM drivers 
WHERE driver_id LIKE 'SURGE_DRV_%' 
ORDER BY driver_id;

-- Show all surge vehicles
SELECT vehicle_id, vehicle_type, depot_id, is_surge_vehicle 
FROM vehicles 
WHERE vehicle_id LIKE 'SURGE_VEH_%' 
ORDER BY vehicle_id;
