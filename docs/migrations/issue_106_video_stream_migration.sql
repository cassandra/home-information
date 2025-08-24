-- Data Migration for Issue #106 - VideoStream Infrastructure Refactor
-- This SQL script provides the same migrations as the Django migration
-- Use for manual verification or direct database migration if needed

-- Pre-Migration Verification Counts
-- Run these queries before migration to understand the impact:

SELECT 'VIDEO_STREAM states to delete' as description, COUNT(*) as count 
FROM entity_entitystate 
WHERE entity_state_type_str = 'video_stream';

SELECT 'ZM cameras to update' as description, COUNT(*) as count 
FROM entity_entity 
WHERE integration_id = 'zm' AND entity_type_str = 'camera';

SELECT 'MOVEMENT sensors to update' as description, COUNT(*) as count 
FROM sense_sensor s
JOIN entity_entitystate es ON s.entity_state_id = es.id
JOIN entity_entity e ON es.entity_id = e.id
WHERE es.entity_state_type_str = 'movement' AND e.integration_id = 'zm';

SELECT 'VIDEO_STREAM delegations to cascade delete' as description, COUNT(*) as count 
FROM entity_entitystatedelegation
WHERE entity_state_id IN (
    SELECT id FROM entity_entitystate 
    WHERE entity_state_type_str = 'video_stream'
);

-- Migration Steps
-- Execute in order:

-- 1. Update ZoneMinder camera entities to have video capability
UPDATE entity_entity 
SET has_video_stream = TRUE 
WHERE integration_id = 'zm' 
  AND entity_type_str = 'camera';

-- 2. Update MOVEMENT sensors for ZM entities to provide video streams
UPDATE sense_sensor
SET provides_video_stream = TRUE
FROM entity_entitystate es
JOIN entity_entity e ON es.entity_id = e.id
WHERE sense_sensor.entity_state_id = es.id
  AND es.entity_state_type_str = 'movement'
  AND e.integration_id = 'zm';

-- 3. Delete VIDEO_STREAM sensors (CASCADE handles SensorHistory)
DELETE FROM sense_sensor
WHERE entity_state_id IN (
    SELECT id FROM entity_entitystate 
    WHERE entity_state_type_str = 'video_stream'
);

-- 4. Delete VIDEO_STREAM EntityStates (CASCADE handles delegations)
DELETE FROM entity_entitystate
WHERE entity_state_type_str = 'video_stream';

-- Post-Migration Verification
-- Run these queries after migration to verify success:

SELECT 'Remaining VIDEO_STREAM states (should be 0)' as check, COUNT(*) as count 
FROM entity_entitystate 
WHERE entity_state_type_str = 'video_stream';

SELECT 'ZM cameras without video capability (should be 0)' as check, COUNT(*) as count 
FROM entity_entity 
WHERE integration_id = 'zm' 
  AND entity_type_str = 'camera' 
  AND has_video_stream = FALSE;

SELECT 'ZM MOVEMENT sensors without video capability (should be 0)' as check, COUNT(*) as count 
FROM sense_sensor s
JOIN entity_entitystate es ON s.entity_state_id = es.id
JOIN entity_entity e ON es.entity_id = e.id
WHERE es.entity_state_type_str = 'movement' 
  AND e.integration_id = 'zm'
  AND s.provides_video_stream = FALSE;