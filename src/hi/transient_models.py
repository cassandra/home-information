from dataclasses import dataclass

from hi.units import UnitQuantity


@dataclass
class GeographicLocation:

    latitude   : float
    longitude  : float
    elevation  : UnitQuantity  = None

    def __str__(self):
        return f'( {self.latitude:.6}, {self.longitude:6} ) [elev={self.elevation}]'
    
    def __hash__( self ):
        lat = round( self.latitude, 6 )
        lon = round( self.longitude, 6 )
        if self.elevation is None:
            elev = None
        else:
            elev = round( self.elevation.to("meters").magnitude )
        return hash( (lat, lon, elev) )

    def __eq__( self, other ):
        if not isinstance( other, GeographicLocation ):
            return False
        lat_equal = round( self.latitude, 6 ) == round( other.latitude, 6 )
        lon_equal = round( self.longitude, 6 ) == round( other.longitude, 6 )
        if self.elevation is None and other.elevation is None:
            elev_equal = True
        elif self.elevation is None or other.elevation is None:
            elev_equal = False
        else:
            elev_equal = round( self.elevation.to("meters").magnitude) \
                == round( other.elevation.to("meters").magnitude)
        return lat_equal and lon_equal and elev_equal
    
