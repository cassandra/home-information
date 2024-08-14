from dataclasses import dataclass
import math
from typing import List

from django.db.models import QuerySet
from django.http import HttpRequest


@dataclass
class Pagination:
    page_number           : int
    page_size             : int
    item_count            : int
    page_number_list      : List[int]
    start_offset          : int   = 0
    end_offset            : int   = 0
    page_count            : int   = 1
    required              : bool  = False
    has_previous_page     : bool  = False
    has_next_page         : bool  = False
    previous_page_number  : bool  = None
    next_page_number      : bool  = None
    has_pages_before      : bool  = False
    has_pages_after       : bool  = False

        
def compute_pagination_from_queryset( request : HttpRequest, query_set : QuerySet, page_size : int = 10 ):
    try:
        page_number = int(request.GET.get( 'page', '1' ))
    except ( ValueError, TypeError ):
        page_number = 1
    item_count = query_set.count()
    return compute_pagination( page_number = page_number,
                               page_size = page_size,
                               item_count = item_count )


def compute_pagination( page_number : int, page_size : int, item_count : int, paging_window : int = 2 ):

    pagination = Pagination(
        page_number = page_number,
        page_size = page_size,
        item_count = item_count,
        page_number_list = [ 1 ],
        end_offset = item_count - 1,
    )

    if pagination.page_size < 1:
        pagination.page_size = 1

    if item_count > 0:
        pagination.page_count = math.ceil( item_count / page_size )
    
    if pagination.page_number < 1:
        pagination.page_number = 1
    if pagination.page_number > pagination.page_count:
        pagination.page_number = pagination.page_count

    if item_count <= page_size:
        return pagination
    
    pagination.required = True

    if pagination.page_number > 1:
        pagination.has_previous_page = True
        pagination.previous_page_number = pagination.page_number - 1
    if pagination.page_number < pagination.page_count:
        pagination.has_next_page = True
        pagination.next_page_number = pagination.page_number + 1
        
    pagination.start_offset = pagination.page_size * ( pagination.page_number - 1 )
    pagination.end_offset = pagination.start_offset + pagination.page_size - 1
    if pagination.end_offset > pagination.item_count:
        pagination.end_offset = pagination.item_count - 1
         
    pagination.page_number_list = list()
    for num in range( pagination.page_number - paging_window,
                      pagination.page_number + paging_window + 1 ):
        if num < 1:
            continue
        if num > pagination.page_count:
            continue
        pagination.page_number_list.append( num )
        continue

    if pagination.page_number_list[0] > 1:
        pagination.has_pages_before = True
    if pagination.page_count > pagination.page_number_list[-1]:        
        pagination.has_pages_after = True
    
    return pagination
