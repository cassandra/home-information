from django.shortcuts import render
from django.views.generic import View

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.hi_styles import EntityStyle


class TestUiEntityHomeView(View):
    """Home view for entity app UI testing."""

    def get(self, request, *args, **kwargs):
        context = {
            'app_name': 'entity',
        }
        return render(request, "entity/tests/ui/home.html", context)


class TestUiEntityTypeVisualBrowserView(View):
    """
    Visual browser for all EntityType representations.
    Shows icons, closed paths, and open paths for all EntityTypes.
    """

    def get(self, request, *args, **kwargs):
        # Get all EntityTypes sorted alphabetically
        all_entity_types = sorted(EntityType, key=lambda et: et.name)

        # Process each EntityType to determine its visual representation
        entity_type_data = []
        for entity_type in all_entity_types:
            data = self.get_entity_type_visual_data(entity_type)
            entity_type_data.append(data)

        context = {
            'entity_type_data': entity_type_data,
            'total_entity_types': len(all_entity_types),
        }
        return render(request, "entity/tests/ui/entity_type_visual_browser.html", context)

    def get_entity_type_visual_data(self, entity_type):
        """Get visual representation data for an EntityType."""
        data = {
            'entity_type': entity_type,
            'name': entity_type.name,
            'label': entity_type.label,
            'visual_type': self.get_visual_type(entity_type),
            'is_registered': entity_type in EntityStyle.EntityTypesWithIcons,
            'svg_item': None,
            'sample_path_data': None,
        }

        if entity_type.requires_position():
            # Icon-based entity
            data['svg_item'] = self.create_svg_icon_item(entity_type)
        elif entity_type.requires_closed_path():
            # Closed path entity
            data['sample_path_data'] = self.create_sample_path_with_real_styling(entity_type, 'closed')
        elif entity_type.requires_open_path():
            # Open path entity
            data['sample_path_data'] = self.create_sample_path_with_real_styling(entity_type, 'open')

        return data

    def get_visual_type(self, entity_type):
        """Determine the visual representation type for an EntityType."""
        if entity_type.requires_open_path():
            return 'Open Path'
        elif entity_type.requires_closed_path():
            return 'Closed Path'
        else:
            return 'Icon'

    def create_svg_icon_item(self, entity_type):
        """Create an SVG icon item for display-only rendering."""
        try:
            # Create a synthetic entity for rendering context
            synthetic_entity = Entity(
                name=f"Test {entity_type.label}",
                entity_type=entity_type,
                integration_id=f'test.{entity_type.name.lower()}',
                integration_name='test_integration'
            )

            # Use SvgItemFactory to create proper display item
            svg_factory = SvgItemFactory()
            svg_item = svg_factory.get_display_only_svg_icon_item(synthetic_entity)
            return svg_item

        except Exception:
            # Return None if there's an issue creating the icon
            return None

    def create_sample_path_with_real_styling(self, entity_type, path_type):
        """Create sample path data using real EntityStyle.get_svg_path_status_style()."""
        # Get the real styling for this entity type
        svg_status_style = EntityStyle.get_svg_path_status_style(entity_type)

        # Create appropriate sample path based on type
        if path_type == 'closed':
            # Closed path (rectangle for demonstration)
            sample_path = 'M 10,10 L 50,10 L 50,50 L 10,50 Z'
        else:
            # Open path (line for demonstration)
            sample_path = 'M 10,30 L 20,25 L 30,35 L 40,30 L 50,30'

        return {
            'svg_path': sample_path,
            'fill_color': svg_status_style.fill_color,
            'stroke_color': svg_status_style.stroke_color,
            'stroke_width': str(svg_status_style.stroke_width),
            'stroke_dasharray': ','.join(map(str, svg_status_style.stroke_dasharray)) if svg_status_style.stroke_dasharray else '',
            'fill_opacity': svg_status_style.fill_opacity,
        }

