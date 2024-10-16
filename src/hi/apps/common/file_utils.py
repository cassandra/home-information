import os
import time


def generate_unique_filename( filename : str ):
    original_name, extension = os.path.splitext( filename )
    timestamp = int( time.time() )
    unique_name = f'{original_name}-{timestamp}{extension}'
    return unique_name
