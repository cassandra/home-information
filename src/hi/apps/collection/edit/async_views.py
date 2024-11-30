import json
import logging

from django.core.exceptions import BadRequest
from django.http import Http404
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import CollectionPosition
from hi.apps.collection.transient_models import CollectionEditData
from hi.apps.collection.view_mixin import CollectionViewMixin
import hi.apps.common.antinode as antinode
from hi.apps.entity.view_mixin import EntityViewMixin
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.location.location_manager import LocationManager

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.hi_async_view import HiSideView

from . import forms

logger = logging.getLogger(__name__)


