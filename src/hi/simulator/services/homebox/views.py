from django.http import Http404
from django.shortcuts import render
from django.views.generic import View

from hi.simulator.services.homebox.sim_models import build_item_api_dict
from hi.simulator.services.homebox.simulator import HomeBoxSimulator


def _api_id_for(fields, sim_entity_id) -> str:
    return fields.item_id or str(sim_entity_id)


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
        return render(
            request,
            'homebox/home.html',
            { 'items': items },
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
