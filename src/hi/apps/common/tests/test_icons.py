import logging

from django.template import Context, Template
from django.test import SimpleTestCase

logging.disable( logging.CRITICAL )


class TestIconAccessibilityAttrs( SimpleTestCase ):

    def render( self, markup : str, **context ) -> str:
        return Template( '{% load icons %}' + markup ).render( Context( context ))

    def test_decorative_icon_is_hidden_from_assistive_tech( self ):
        rendered = self.render( '{% icon "close" %}' )
        self.assertIn( 'aria-hidden="true"', rendered )
        self.assertNotIn( 'role="img"', rendered )
        return

    def test_labeled_icon_is_an_image_with_escaped_label( self ):
        rendered = self.render( '{% icon "eye" aria_label=label title="Tip" %}', label = 'Show "x" <b>' )
        self.assertIn( 'aria-label="Show &quot;x&quot; &lt;b&gt;" role="img" title="Tip"', rendered )
        self.assertNotIn( 'aria-hidden', rendered )
        return
