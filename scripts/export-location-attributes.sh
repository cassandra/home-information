#!/bin/bash
#
# Export all custom Location attributes from Home Information database
# This shows all user-added information for locations (floors, areas, etc.)
#
# Usage: ./scripts/export-location-attributes.sh
#

# Database location (adjust if your installation differs)
DB_PATH="${HOME}/.hi/database/hi.sqlite3"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    echo "Please check your Home Information installation path"
    exit 1
fi

# Query to extract custom location attributes with their associated location names
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
            a.value
    END AS attribute_value,
    a.value_type_str AS value_type,
    datetime(a.created_datetime) AS created_date,
    datetime(a.updated_datetime) AS updated_date
FROM 
    location_locationattribute a
    INNER JOIN location_location l ON a.location_id = l.id
WHERE 
    a.attribute_type_str = 'custom'
ORDER BY 
    l.name, 
    a.name;
SQL