#!/bin/bash
#
# Export all custom Item (Entity) attributes from Home Information database
# This shows all user-added information for items in your home
#
# Usage: ./scripts/export-item-attributes.sh
#

# Database location (adjust if your installation differs)
DB_PATH="${HOME}/.hi/database/hi.sqlite3"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    echo "Please check your Home Information installation path"
    exit 1
fi

# Query to extract custom item attributes with their associated item names
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
            a.value
    END AS attribute_value,
    a.value_type_str AS value_type,
    datetime(a.created_datetime) AS created_date,
    datetime(a.updated_datetime) AS updated_date
FROM 
    entity_entityattribute a
    INNER JOIN entity_entity e ON a.entity_id = e.id
WHERE 
    a.attribute_type_str = 'custom'
ORDER BY 
    e.name, 
    a.name;
SQL
