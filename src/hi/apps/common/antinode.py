"""
Helper routines for antinode.js when using this for AJAX-y things.
Normally you can just set the tag attributes data-async
when it is a simple call and replace, but for alternative response flows
these routines provide the convenience wrappers around the antinode.js
specific things.
"""
import json
from django.http import HttpResponse
from django.template.loader import get_template


def normalize_content( content ):
    if isinstance( content, HttpResponse ):
        return content.content.decode('utf-8' )                
    if isinstance( content, str ):
        return content
    raise ValueError( f'Unknown content type. Cannot normalize for async response: {content}.' )


def http_response( data, status=200 ):
    return HttpResponse( json.dumps(data),
                         content_type='application/json',
                         status = status,
                         )


def modal_from_content( request, content, status=200 ):
    """
    Use this when the data-async target was not a modal, but you want
    the internal error message to be displayed in a modal instead of replacing
    the target content.
    """
    return http_response( { 'modal': content }, status = status )


def modal_from_template( request, template_name, context={}, status=200 ):
    """
    Use this when the data-async target was not a modal, but you want
    the internal error message to be displayed in a modal instead of replacing
    the target content.  The template should be set up to contain the necessary
    modal structure (modulo the main wrapper modal div).
    """
    template = get_template( template_name )
    content = template.render( context, request = request )
    return modal_from_content( request, content, status = status )


def refresh_response():
    return http_response( { 'refresh': True } )


def redirect_response( url ):
    return http_response( { 'location': url } )


def response_as_dict( main_content = None, 
                      replace_map = None, 
                      insert_map = None, 
                      append_map = None,
                      set_attributes_map = None,
                      modal_content = None,
                      push_url = None,
                      reset_scrollbar = False,
                      scroll_to = None ):
    """
    In concert with the Javascript handling of synchronous replies,
    this will allow returning multiple pieces of content in one reply
    for the cases where the request has altered more than one area
    of the page.  The 'main_content' will be rendered in whatever
    the 'data-async' value that was specified, while the 'replace_map' should
    be a map from an html tag id to the html content to populate.

    The 'replace_map' is a full replacement of the previous content,
    so usually should have the same html tag id as what it replaces.

    The 'insert_map' is used when you only want to replace the contents
    of the given node and not the node itself.

    The 'append_map' is for content you want appended to the given id
    list of child content.
    
    The 'scroll_to' parameter can be used to automatically scroll to a 
    specific element ID after all DOM updates are complete.
    """
    response_dict = {}

    if main_content and isinstance( main_content, HttpResponse ):
        main_content = main_content.content.decode('utf-8' )
        
    if main_content is not None:
        response_dict['html'] = str(main_content)
    if replace_map is not None:
        response_dict['replace'] = replace_map
    if insert_map is not None:
        response_dict['insert'] = insert_map
    if append_map is not None:
        response_dict['append'] = append_map
    if set_attributes_map is not None:
        response_dict['setAttributes'] = set_attributes_map
    if modal_content is not None:
        response_dict['modal'] = modal_content
    if push_url is not None:
        response_dict['pushUrl'] = push_url
    if reset_scrollbar:
        response_dict['resetScrollbar'] = 'true'
    if scroll_to is not None:
        response_dict['scrollTo'] = scroll_to
    return response_dict


def response( main_content = None, 
              replace_map = None, 
              insert_map = None, 
              append_map = None,
              set_attributes_map = None,
              modal_content = None,
              push_url = None,
              reset_scrollbar = False,
              scroll_to = None,
              status = 200 ):
    
    response_dict = response_as_dict(
        main_content = main_content,
        replace_map = replace_map,
        insert_map = insert_map,
        append_map = append_map,
        set_attributes_map = set_attributes_map,
        modal_content = modal_content,
        push_url = push_url,
        reset_scrollbar = reset_scrollbar,
        scroll_to = scroll_to,
    )
    return http_response( response_dict, status=status )

    
