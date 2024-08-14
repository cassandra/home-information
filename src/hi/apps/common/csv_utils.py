import csv
from dataclasses import dataclass
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class CsvReader:

    filename                   : str
    schema                     : List[ str ]  = None
    label                      : str          = ''
    short_circuit_testing      : int          = None
    key_to_store_extra_fields  : str          = None
    value_for_missing_fields   : object       = None

    def __enter__(self):
        self._lines = 0
        self._csv_file = open( self.filename, 'r', encoding='utf-8' )
        sample = self._csv_file.read( 2048 )
        self._dialect = csv.Sniffer().sniff( sample )
        self._csv_file.seek(0)
        self._dict_reader = csv.DictReader( self._csv_file,
                                            fieldnames = self.schema,
                                            restkey = self.key_to_store_extra_fields,
                                            restval = self.value_for_missing_fields,
                                            dialect = self._dialect )
        self._header_fields = self._dict_reader.fieldnames
        return self

    @property
    def header_fields(self):
        return self._header_fields

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._csv_file:
            return
        self._csv_file.close()
        self._csv_file = None
        self._dict_reader = None
        return

    def __iter__(self):
        return self

    def __next__(self):
        if not self._dict_reader:
            raise StopIteration()
        if self.short_circuit_testing and ( self._lines >= self.short_circuit_testing ):
            raise StopIteration()

        value_map = next(self._dict_reader)
        self._lines += 1
        return value_map


@dataclass
class CsvWriter:

    filename : str
    schema   : List

    def __enter__(self):
        self._lines = 0
        self._csv_file = open( self.filename, 'w', encoding='utf-8', newline = '' )
        self._dict_writer = csv.DictWriter( self._csv_file,
                                            fieldnames = self.schema,
                                            lineterminator = "\n",
                                            delimiter = ',',
                                            quotechar = '"',
                                            quoting = csv.QUOTE_MINIMAL )
        self._dict_writer.writeheader()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._csv_file:
            return
        self._csv_file.close()
        self._csv_file = None
        self._dict_writer = None
        return

    def write( self, value_map : Dict ):
        self._dict_writer.writerow( value_map )
        self._lines += 1
        return
