import logging

from django.test import TestCase

from hi.apps.common.pagination import compute_pagination

logging.disable(logging.CRITICAL)


class PaginationTestCase(TestCase):

    def test_compute_pagination(self):

        ##########
        # Simple one pager
        
        pagination = compute_pagination( page_number = 1, page_size = 10,
                                         item_count = 5, paging_window = 7 )
        self.assertEqual( 1, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 5, pagination.item_count )
        self.assertEqual( [ 1 ], pagination.page_number_list )
        self.assertEqual( 0, pagination.start_offset )
        self.assertEqual( 4, pagination.end_offset )
        self.assertEqual( 1, pagination.page_count )
        self.assertEqual( False, pagination.required )
        self.assertEqual( False, pagination.has_previous_page )
        self.assertEqual( False, pagination.has_next_page )
        self.assertEqual( None, pagination.previous_page_number )
        self.assertEqual( None, pagination.next_page_number )
        self.assertEqual( False, pagination.has_pages_before )
        self.assertEqual( False, pagination.has_pages_after )

        ##########
        # Zero page number
        
        pagination = compute_pagination( page_number = 0, page_size = 10,
                                         item_count = 5, paging_window = 7 )
        self.assertEqual( 1, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 5, pagination.item_count )
        self.assertEqual( [ 1 ], pagination.page_number_list )
        self.assertEqual( 0, pagination.start_offset )
        self.assertEqual( 4, pagination.end_offset )
        self.assertEqual( 1, pagination.page_count )
        self.assertEqual( False, pagination.required )
        self.assertEqual( False, pagination.has_previous_page )
        self.assertEqual( False, pagination.has_next_page )
        self.assertEqual( None, pagination.previous_page_number )
        self.assertEqual( None, pagination.next_page_number )
        self.assertEqual( False, pagination.has_pages_before )
        self.assertEqual( False, pagination.has_pages_after )

        ##########
        # Zero items with high page number
        
        pagination = compute_pagination( page_number = 22, page_size = 10,
                                         item_count = 0, paging_window = 7 )
        self.assertEqual( 1, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 0, pagination.item_count )
        self.assertEqual( [ 1 ], pagination.page_number_list )
        self.assertEqual( 0, pagination.start_offset )
        self.assertEqual( -1, pagination.end_offset )
        self.assertEqual( 1, pagination.page_count )
        self.assertEqual( False, pagination.required )
        self.assertEqual( False, pagination.has_previous_page )
        self.assertEqual( False, pagination.has_next_page )
        self.assertEqual( None, pagination.previous_page_number )
        self.assertEqual( None, pagination.next_page_number )
        self.assertEqual( False, pagination.has_pages_before )
        self.assertEqual( False, pagination.has_pages_after )

        ##########
        # Exactly one page
        
        pagination = compute_pagination( page_number = 1, page_size = 10,
                                         item_count = 10, paging_window = 7 )
        self.assertEqual( 1, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 10, pagination.item_count )
        self.assertEqual( [ 1 ], pagination.page_number_list )
        self.assertEqual( 0, pagination.start_offset )
        self.assertEqual( 9, pagination.end_offset )
        self.assertEqual( 1, pagination.page_count )
        self.assertEqual( False, pagination.required )
        self.assertEqual( False, pagination.has_previous_page )
        self.assertEqual( False, pagination.has_next_page )
        self.assertEqual( None, pagination.previous_page_number )
        self.assertEqual( None, pagination.next_page_number )
        self.assertEqual( False, pagination.has_pages_before )
        self.assertEqual( False, pagination.has_pages_after )

        ##########
        # Exactly one more than a page
        
        pagination = compute_pagination( page_number = 1, page_size = 10,
                                         item_count = 11, paging_window = 7 )
        self.assertEqual( 1, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 11, pagination.item_count )
        self.assertEqual( [ 1, 2 ], pagination.page_number_list )
        self.assertEqual( 0, pagination.start_offset )
        self.assertEqual( 9, pagination.end_offset )
        self.assertEqual( 2, pagination.page_count )
        self.assertEqual( True, pagination.required )
        self.assertEqual( False, pagination.has_previous_page )
        self.assertEqual( True, pagination.has_next_page )
        self.assertEqual( None, pagination.previous_page_number )
        self.assertEqual( 2, pagination.next_page_number )
        self.assertEqual( False, pagination.has_pages_before )
        self.assertEqual( False, pagination.has_pages_after )

        ##########
        # Second page when exactly one more than a page
        
        pagination = compute_pagination( page_number = 2, page_size = 10,
                                         item_count = 11, paging_window = 7 )
        self.assertEqual( 2, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 11, pagination.item_count )
        self.assertEqual( [ 1, 2 ], pagination.page_number_list )
        self.assertEqual( 10, pagination.start_offset )
        self.assertEqual( 10, pagination.end_offset )
        self.assertEqual( 2, pagination.page_count )
        self.assertEqual( True, pagination.required )
        self.assertEqual( False, pagination.has_next_page )
        self.assertEqual( 1, pagination.previous_page_number )
        self.assertEqual( None, pagination.next_page_number )
        self.assertEqual( False, pagination.has_pages_before )
        self.assertEqual( False, pagination.has_pages_after )

        ##########
        # Deeper results
        
        pagination = compute_pagination( page_number = 15, page_size = 10,
                                         item_count = 999, paging_window = 3 )
        self.assertEqual( 15, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 999, pagination.item_count )
        self.assertEqual( [ 12, 13, 14, 15, 16, 17, 18 ], pagination.page_number_list )
        self.assertEqual( 140, pagination.start_offset )
        self.assertEqual( 149, pagination.end_offset )
        self.assertEqual( 100, pagination.page_count )
        self.assertEqual( True, pagination.required )
        self.assertEqual( True, pagination.has_previous_page )
        self.assertEqual( True, pagination.has_next_page )
        self.assertEqual( 14, pagination.previous_page_number )
        self.assertEqual( 16, pagination.next_page_number )
        self.assertEqual( True, pagination.has_pages_before )
        self.assertEqual( True, pagination.has_pages_after )

        ##########
        # Deeper results with wider paging window
        
        pagination = compute_pagination( page_number = 15, page_size = 10,
                                         item_count = 999, paging_window = 5 )
        self.assertEqual( 15, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 999, pagination.item_count )
        self.assertEqual( [ 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 ], pagination.page_number_list )
        self.assertEqual( 140, pagination.start_offset )
        self.assertEqual( 149, pagination.end_offset )
        self.assertEqual( 100, pagination.page_count )
        self.assertEqual( True, pagination.required )
        self.assertEqual( True, pagination.has_previous_page )
        self.assertEqual( True, pagination.has_next_page )
        self.assertEqual( 14, pagination.previous_page_number )
        self.assertEqual( 16, pagination.next_page_number )

        ##########
        # Last page
        
        pagination = compute_pagination( page_number = 100, page_size = 10,
                                         item_count = 999, paging_window = 3 )
        self.assertEqual( 100, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 999, pagination.item_count )
        self.assertEqual( [ 97, 98, 99, 100 ], pagination.page_number_list )
        self.assertEqual( 990, pagination.start_offset )
        self.assertEqual( 999, pagination.end_offset )
        self.assertEqual( 100, pagination.page_count )
        self.assertEqual( True, pagination.required )
        self.assertEqual( True, pagination.has_previous_page )
        self.assertEqual( False, pagination.has_next_page )
        self.assertEqual( 99, pagination.previous_page_number )
        self.assertEqual( None, pagination.next_page_number )
        self.assertEqual( True, pagination.has_pages_before )
        self.assertEqual( False, pagination.has_pages_after )

        ##########
        # Beyond last page
        
        pagination = compute_pagination( page_number = 116, page_size = 10,
                                         item_count = 999, paging_window = 3 )
        self.assertEqual( 100, pagination.page_number )
        self.assertEqual( 10, pagination.page_size )
        self.assertEqual( 999, pagination.item_count )
        self.assertEqual( [ 97, 98, 99, 100 ], pagination.page_number_list )
        self.assertEqual( 990, pagination.start_offset )
        self.assertEqual( 999, pagination.end_offset )
        self.assertEqual( 100, pagination.page_count )
        self.assertEqual( True, pagination.required )
        self.assertEqual( True, pagination.has_previous_page )
        self.assertEqual( False, pagination.has_next_page )
        self.assertEqual( 99, pagination.previous_page_number )
        self.assertEqual( None, pagination.next_page_number )
        self.assertEqual( True, pagination.has_pages_before )
        self.assertEqual( False, pagination.has_pages_after )

        return
