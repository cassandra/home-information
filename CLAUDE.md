# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Environment Setup
```bash
# Initialize development environment (one-time setup)
make env-build-dev
python3.11 -m venv venv
. ./init-env-dev.sh
pip install -r src/hi/requirements/development.txt

# Daily development setup
. ./init-env-dev.sh  # Sources virtual env and environment variables
```

### Django Management
```bash
cd src

# Database operations
./manage.py migrate
./manage.py makemigrations
./manage.py check

# Testing
./manage.py test                    # Run all unit tests
./manage.py test weather.tests     # Run specific app tests

# User management
./manage.py hi_createsuperuser
./manage.py hi_creategroups

# Development server
./manage.py runserver              # Runs on http://127.0.0.1:8411
```

### Code Quality
```bash
# Linting and formatting (from development.txt requirements)
black src/                         # Format code
flake8 src/                       # Lint code
autopep8 --in-place --recursive src/  # Auto-format
```

### Docker Operations
```bash
# Build and run in containers
make docker-build
make docker-run-fg                 # Foreground
make docker-run                    # Background
make docker-stop
```

## Architecture Overview

### Core Django Applications

**Entity App**: Central model for all physical/logical objects (devices, features, software). Uses integration keys for external system connectivity and supports SVG-based positioning.

**Location App**: Physical space management with SVG-based floor plans. Manages hierarchical locations and spatial positioning of entities and collections.

**Sense App**: Sensor data collection and monitoring. Links to EntityState with history persistence for various sensor types.

**Control App**: Device control and automation. Manages controllable devices with action history tracking.

**Event App**: Event-driven automation system with multi-clause triggers, time windows, and automated responses.

**Alert App**: Alert and alarm management using singleton pattern with queue-based processing.

**Collection App**: Logical grouping and organization of entities for management and display.

**Weather App**: Weather data integration with pluggable sources (NWS) and data aggregation.

### Integration Layer

**Home Assistant Integration** (`src/hi/services/hass/`): Full two-way sync with Home Assistant including entity mapping, state synchronization, and controller integration.

**ZoneMinder Integration** (`src/hi/services/zoneminder/`): Camera and video surveillance system integration for security monitoring.

**Integration Pattern**: All external systems use integration keys for mapping entities between systems.

### Key Architectural Patterns

- **Entity-Centric Design**: All controllable/observable items modeled as entities with states
- **Singleton Managers**: Core functionality uses singleton pattern (AlertManager, WeatherManager)
- **SVG-Based Visualization**: Locations and entities support SVG graphics for spatial representation
- **Mixin Pattern**: Common functionality shared through mixins (SecurityMixins, NotifyMixins)
- **Event-Driven Architecture**: Automated responses based on state changes and sensor readings

### File Structure Conventions

- `apps/*/models.py`: Django models for each application
- `apps/*/managers.py`: Business logic managers (often singletons)
- `apps/*/transient_models.py`: Non-database models for data transfer
- `apps/*/templates/*/panes/`: UI component templates
- `apps/*/templates/*/modals/`: Modal dialog templates
- `apps/*/tests/`: Unit tests and test data
- `integrations/`: Cross-system integration framework
- `services/*/`: External service integrations (HASS, ZoneMinder)

### Database and Dependencies

- **Database**: SQLite for development, supports PostgreSQL for production
- **Cache**: Redis required for development and production
- **Frontend**: jQuery 3.7, Bootstrap 4, custom SVG manipulation
- **Python**: 3.11+, Django 4.2

### Testing Infrastructure

- Unit tests: `./manage.py test`
- Visual testing pages: Available at `/tests/ui` when `DEBUG=True`
- Integration tests: Custom management commands (`hass_test`, `zm_test`)

### Security and Configuration

- Environment variables managed via `.private/env/` (not committed)
- Settings split by environment: `development.py`, `production.py`, `staging.py`
- Security app manages access control and monitoring states
- Config app provides centralized system configuration storage

## Coding Style Guidelines

### Control Flow Statements
- Always include explicit `continue` statements in loops, even when not syntactically required
- Always include explicit `return` statements in functions, even when not syntactically required
- This improves code readability and makes control flow intentions explicit

### Operator Spacing
- Use spaces around assignment operators and most other operators in expressions
- Examples: `x = y + z`, `result += value`, `if count == 0`, `total -= amount`
- Exception: Don't add spaces in function keyword arguments (`func(x=y)`) or type annotations (`x: int = 5`)

Example:
```python
def process_items(items):
    results = []
    for item in items:
        if not item.valid:
            continue  # Explicit continue for invalid items
        
        if item.needs_processing:
            result = process(item)
            results.append(result)
            continue  # Explicit continue after processing
        
        # Handle non-processing case
        results.append(item.default_value)
        continue  # Explicit continue at end of loop
    
    return results  # Explicit return at end of function

def simple_function():
    print("Hello world")
    return  # Explicit return even for void functions
```

### General Guidelines
- Follow existing code patterns and conventions in the codebase
- Use descriptive variable and function names
- Maintain consistency with Django and Python best practices

## Git Commit Guidelines

### Commit Message Style
- Use concise, descriptive commit messages without attribution text
- Focus on **what** was changed and **why**, not implementation details
- Keep messages professional and project-focused
- **Do NOT include** Claude Code attribution, co-author tags, or generated-by comments

**Good examples:**
```
Fix weather module unit test failures and improve WMO units handling
Add support for temperature offset unit arithmetic in Pint
Remove invalid AlertUrgency.PAST enum value for weather alerts
```

**Avoid:**
```
🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```