from django.shortcuts import render
from django.template.loader import get_template
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.constants import DIVID


class EditStartView( View ):

    def get(self, request, *args, **kwargs):

        div_id_to_template_name = {
            DIVID['TOP'] : 'edit/panes/top.html',
            DIVID['BOTTOM'] : 'edit/panes/bottom.html',
            DIVID['MAIN'] : 'edit/panes/main.html',
            DIVID['SIDE'] : 'edit/panes/side.html',
        }
        
        context = {
        }

        insert_map = dict()
        for div_id, template_name in div_id_to_template_name.items():
            template = get_template( template_name )
            content = template.render( context, request = request )
            insert_map[div_id] = content,
            continue
        
        return antinode.response(
            insert_map = insert_map,
        )
    
