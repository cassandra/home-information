from django.core.exceptions import BadRequest
from django.http import Http404
from django.shortcuts import render
from django.views.generic import View

from hi.simulator.services.homebox.sim_models import build_item_api_dict
from hi.simulator.services.homebox.simulator import HbApiVersion, HomeBoxSimulator


def _api_id_for(fields, sim_entity_id) -> str:
    return fields.item_id or str(sim_entity_id)


def _api_version_context(simulator: HomeBoxSimulator) -> dict:
    return {
        'api_version': simulator.api_version,
        'api_version_choices': list( HbApiVersion ),
    }


class HomeView( View ):

    def get(self, request, *args, **kwargs):
        simulator = HomeBoxSimulator()
        items = []
        for ( sim_entity_id, fields, archived_state,
              created_at, updated_at ) in simulator.get_sim_entity_pairs():
            items.append({
                'id'   : _api_id_for( fields, sim_entity_id ),
                'name' : fields.name,
            })
        items.sort( key = lambda row: row['name'] )
        context = { 'items': items }
        context.update( _api_version_context( simulator ) )
        return render(
            request,
            'homebox/home.html',
            context,
        )


class SetApiVersionView( View ):
    """Operator toggle for the HomeBox simulator's served API
    version. Used to exercise the integration's dual-API client
    (#373) against both v0.25 (``/v1/items/*``) and v0.26+
    (``/v1/entities/*``) shapes without needing two HomeBox
    installs."""

    TEMPLATE_NAME = 'homebox/panes/api_version_form.html'

    def post(self, request, *args, **kwargs):
        simulator = HomeBoxSimulator()
        api_version_name = request.POST.get('api_version')
        try:
            api_version = HbApiVersion[ api_version_name ]
        except (KeyError, TypeError):
            raise BadRequest( f'Invalid api_version: {api_version_name}' )
        simulator.set_api_version( api_version )
        return render(
            request,
            self.TEMPLATE_NAME,
            _api_version_context( simulator ),
        )


class ItemView( View ):

    def get(self, request, *args, **kwargs):
        item_id = kwargs.get('item_id')
        simulator = HomeBoxSimulator()
        for ( sim_entity_id, fields, archived_state,
              created_at, updated_at ) in simulator.get_sim_entity_pairs():
            if _api_id_for( fields, sim_entity_id ) != item_id:
                continue
            item = build_item_api_dict(
                sim_entity_id  = sim_entity_id,
                fields         = fields,
                archived_state = archived_state,
                created_at     = created_at,
                updated_at     = updated_at,
            )
            return render(
                request,
                'homebox/item.html',
                { 'item': item },
            )
        raise Http404( f'Item {item_id} not found' )
