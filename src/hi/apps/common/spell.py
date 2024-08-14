from dataclasses import dataclass, field
import logging
import re
from spellchecker import SpellChecker
from typing import List

from waa.apps.common.singleton import Singleton

logger = logging.getLogger(__name__)


@dataclass
class SpellingCorrection:
    text                  : str
    misspelled_word_list  : List[ str ]   = field( default_factory = list )

    @property
    def misspelled_count(self):
        return len(self.misspelled_word_list)
    
    
class Spelling(Singleton):
    
    def __init_singleton__( self ):
        self._spell = SpellChecker()
        return
    
    def get_spelling_corrections( self, text : str ) -> List[SpellingCorrection]:

        original_word_list = re.split( r'\s+', text ) 
        misspelled = self._spell.unknown( original_word_list )

        new_word_list = list()
        misspelled_word_list = list()
        for original_word in original_word_list:
            if original_word in misspelled:
                corrected_word = self._spell.correction( original_word )
                if corrected_word == original_word:
                    new_word_list.append( original_word )
                elif corrected_word:
                    new_word_list.append( corrected_word )
                    misspelled_word_list.append( original_word )
                else:
                    new_word_list.append( original_word )
            else:
                new_word_list.append( original_word )
                    
            continue

        new_text = ' '.join( new_word_list )
        return [ SpellingCorrection( text = new_text, misspelled_word_list = misspelled_word_list ) ]
