#!/bin/bash
#
# Export all custom attributes (both Items and Locations) from Home Information database
# Provides a complete export of all user-added information
#
# Usage: ./scripts/export-all-attributes.sh
#

# Database location (adjust if your installation differs)
DB_PATH="${HOME}/.hi/database/hi.sqlite3"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    echo "Please check your Home Information installation path"
    exit 1
fi

echo "=================================================================================="
echo "ITEM (ENTITY) ATTRIBUTES"
echo "=================================================================================="
echo

sqlite3 -header -column "$DB_PATH" <<'SQL'
SELECT 
    e.name AS item_name,
    e.entity_type_str AS item_type,
    a.name AS attribute_name,
    CASE 
        WHEN a.value_type_str = 'file' THEN 
            'File: ' || a.file_value
        WHEN a.value IS NULL OR a.value = '' THEN 
            '(empty)'
        ELSE 
            substr(a.value, 1, 50) || 
            CASE WHEN length(a.value) > 50 THEN '...' ELSE '' END
    END AS attribute_value,
    a.value_type_str AS value_type,
    date(a.created_datetime) AS created
FROM 
    entity_entityattribute a
    INNER JOIN entity_entity e ON a.entity_id = e.id
WHERE 
    a.attribute_type_str = 'custom'
ORDER BY 
    e.name, 
    a.name;
SQL

echo
echo "=================================================================================="
echo "LOCATION ATTRIBUTES"
echo "=================================================================================="
echo

sqlite3 -header -column "$DB_PATH" <<'SQL'
SELECT 
    l.name AS location_name,
    a.name AS attribute_name,
    CASE 
        WHEN a.value_type_str = 'file' THEN 
            'File: ' || a.file_value
        WHEN a.value IS NULL OR a.value = '' THEN 
            '(empty)'
        ELSE 
            substr(a.value, 1, 50) || 
            CASE WHEN length(a.value) > 50 THEN '...' ELSE '' END
    END AS attribute_value,
    a.value_type_str AS value_type,
    date(a.created_datetime) AS created
FROM 
    location_locationattribute a
    INNER JOIN location_location l ON a.location_id = l.id
WHERE 
    a.attribute_type_str = 'custom'
ORDER BY 
    l.name, 
    a.name;
SQL

echo
echo "=================================================================================="
echo "SUMMARY"
echo "=================================================================================="

sqlite3 "$DB_PATH" <<'SQL'
SELECT 
    printf('Total Item Attributes: %d', 
        (SELECT COUNT(*) FROM entity_entityattribute WHERE attribute_type_str = 'custom'))
UNION ALL
SELECT 
    printf('Total Location Attributes: %d', 
        (SELECT COUNT(*) FROM location_locationattribute WHERE attribute_type_str = 'custom'))
UNION ALL
SELECT 
    printf('Total Files Uploaded: %d',
        (SELECT COUNT(*) FROM entity_entityattribute WHERE attribute_type_str = 'custom' AND value_type_str = 'file' AND file_value IS NOT NULL) +
        (SELECT COUNT(*) FROM location_locationattribute WHERE attribute_type_str = 'custom' AND value_type_str = 'file' AND file_value IS NOT NULL));
SQL