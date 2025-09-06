# Home Information Data Export Scripts

This directory contains utility scripts for managing your Home Information instalation.

## Available Scripts

### export-item-attributes.sh
Exports all custom attributes for items (entities) in your home, including:
- Item name and type
- Attribute names and values
- File references
- Creation and update timestamps

**Usage:**
```bash
./scripts/export-item-attributes.sh
```

### export-location-attributes.sh
Exports all custom attributes for locations (floors, areas, rooms), including:
- Location name
- Attribute names and values
- File references
- Creation and update timestamps

**Usage:**
```bash
./scripts/export-location-attributes.sh
```

### export-all-attributes.sh
Provides a comprehensive export of all custom attributes (both items and locations) with a summary.

**Usage:**
```bash
./scripts/export-all-attributes.sh
```

## Output Formats

You can redirect the output to save it in different formats:

**Save as text file:**
```bash
./scripts/export-all-attributes.sh > my-home-data.txt
```

**Export directly as CSV (comma-separated values):**
```bash
# Export item attributes as CSV
sqlite3 -csv ~/.hi/database/hi.sqlite3 "SELECT e.name AS item_name, e.entity_type_str AS item_type, a.name AS attribute_name, a.value AS attribute_value FROM entity_entityattribute a INNER JOIN entity_entity e ON a.entity_id = e.id WHERE a.attribute_type_str = 'custom';" > items.csv

# Export location attributes as CSV  
sqlite3 -csv ~/.hi/database/hi.sqlite3 "SELECT l.name AS location_name, a.name AS attribute_name, a.value AS attribute_value FROM location_locationattribute a INNER JOIN location_location l ON a.location_id = l.id WHERE a.attribute_type_str = 'custom';" > locations.csv
```

## Direct Database Access

If you need more control, you can query the SQLite database directly:

```bash
# Open interactive SQLite session
sqlite3 ~/.hi/database/hi.sqlite3

# List all tables
.tables

# Show schema for a table
.schema entity_entityattribute

# Export specific data
.mode csv
.output my-data.csv
SELECT * FROM entity_entityattribute WHERE attribute_type_str = 'custom';
.quit
```

## Data Portability

Your Home Information data is stored in open, standard formats:
- **Database**: SQLite at `~/.hi/database/hi.sqlite3`
- **Files**: Regular files at `~/.hi/media/`

This ensures you always have full access to your data without requiring Home Information to be running.
