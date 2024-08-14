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
    template = get_template(template_name)
    content = template.render(context, request=request)
    return modal_from_content( request, content, status = status )


def refresh_response():
    return http_response( { 'refresh': True } )


def redirect_response( url ):
    return http_response( { 'location': url } )


def response_as_dict( mainContent=None, 
                      replaceMap=None, 
                      insertMap=None, 
                      appendMap=None,
                      modalContent=None,
                      pushUrl = None,
                      resetScrollbar = False ):
    """
    In concert with the Javascript handling of synchronous replies,
    this will allow returning multiple pieces of content in one reply
    for the cases where the request has altered more than one area
    of the page.  The 'mainContent' will be rendered in whatever
    the 'data-async' value that was specified, while the 'replaceMap' should
    be a map from an html tag id to the html content to populate.

    The 'replaceMap' is a full replacement of the previous content,
    so usually should have the same html tag id as what it replaces.

    The 'insertMap' is used when you only want to replace the contents
    of the given node and not the node itself.

    The 'appendMap' is for content you want appended to the given id
    list of child content.
    """
    response_dict = {}

    if mainContent and isinstance( mainContent, HttpResponse ):
        mainContent = mainContent.content.decode('utf-8' )
        
    if mainContent is not None:
        response_dict['html'] = str(mainContent)
    if replaceMap is not None:
        response_dict['replace'] = replaceMap
    if insertMap is not None:
        response_dict['insert'] = insertMap
    if appendMap is not None:
        response_dict['append'] = appendMap
    if modalContent is not None:
        response_dict['modal'] = modalContent
    if pushUrl is not None:
        response_dict['pushUrl'] = pushUrl
    if resetScrollbar:
        response_dict['resetScrollbar'] = 'true'
    return response_dict


def response( mainContent = None, 
              replaceMap = None, 
              insertMap = None, 
              appendMap = None,
              modalContent = None,
              pushUrl = None,
              resetScrollbar = False,
              status = 200 ):
    
    response_dict = response_as_dict( mainContent = mainContent,
                                      replaceMap = replaceMap,
                                      insertMap = insertMap,
                                      appendMap = appendMap,
                                      modalContent = modalContent,
                                      pushUrl = pushUrl,
                                      resetScrollbar = resetScrollbar,
                                      )
    return http_response( response_dict, status=status )

    
