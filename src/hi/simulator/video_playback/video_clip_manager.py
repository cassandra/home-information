"""Pre-canned camera footage: discovery + frame serving for the simulator.

A clip is a directory of alphabetically-ordered JPEG frames under
``settings.SIMULATOR_VIDEO_DIR``; the subdirectory names are the operator's
``live_clip`` / ``event_clip`` choices. The clip set is scanned once per
process (restart the simulator to pick up new clips); each clip's frame list is
listed lazily and cached. Platform-neutral so the Frigate and ZoneMinder
simulators serve from the identical source.
"""
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

from django.conf import settings

from hi.apps.common.singleton import Singleton

logger = logging.getLogger(__name__)

# Reserved value meaning "no clip selected — use the synthesized placeholder"
# (today's behavior). Never a directory name.
SYNTHETIC_CLIP_VALUE = 'synthetic'


class VideoClipManager( Singleton ):

    VIDEO_FPS = 5  # frames/sec for the looping live-feed illusion
    _JPEG_EXTENSIONS = ( '.jpg', '.jpeg' )

    def __init_singleton__( self ):
        self._clip_names : Optional[ List[ str ] ] = None
        self._frames_by_clip : Dict[ str, List[ str ] ] = {}
        self._mp4_by_clip : Dict[ str, Optional[ str ] ] = {}
        return

    def get_clip_choices( self ) -> List[ Tuple[ str, str ] ]:
        """Discrete-state choices: the synthetic placeholder plus every clip."""
        choices = [ ( SYNTHETIC_CLIP_VALUE, 'Synthetic (placeholder)' ) ]
        for clip_name in self.get_clip_names():
            choices.append( ( clip_name, clip_name ) )
            continue
        return choices

    def get_clip_names( self ) -> List[ str ]:
        """Sorted clip (subdirectory) names, scanned once per process."""
        if self._clip_names is None:
            self._clip_names = self._scan_clip_names()
        return self._clip_names

    def live_frame_bytes( self, clip_name : str ) -> Optional[ bytes ]:
        """Frame at the current wall-clock index (looping at VIDEO_FPS) — the
        moving live-feed illusion. None when synthetic / missing / empty."""
        frames = self._selectable_frames( clip_name )
        if not frames:
            return None
        index = int( time.monotonic() * self.VIDEO_FPS ) % len( frames )
        return self._read_frame( frames[ index ] )

    def event_frame_bytes( self, clip_name : str ) -> Optional[ bytes ]:
        """A single representative frame (the middle of the clip). None when
        synthetic / missing / empty."""
        frames = self._selectable_frames( clip_name )
        if not frames:
            return None
        return self._read_frame( frames[ len( frames ) // 2 ] )

    def has_clip_frames( self, clip_name : str ) -> bool:
        return bool( self._selectable_frames( clip_name ))

    def clip_mp4_path( self, clip_name : str ) -> Optional[ str ]:
        """Path to the clip's pre-rendered MP4 (the single ``*.mp4`` in its
        directory), or None when synthetic / missing / no mp4 present. Lets
        Frigate's event-clip endpoint serve a pre-canned file directly — no
        runtime transcoding; the mp4 is built offline by the import tool."""
        if not clip_name or clip_name == SYNTHETIC_CLIP_VALUE:
            return None
        if clip_name not in self._mp4_by_clip:
            self._mp4_by_clip[ clip_name ] = self._scan_clip_mp4( clip_name )
        return self._mp4_by_clip[ clip_name ]

    def _scan_clip_mp4( self, clip_name : str ) -> Optional[ str ]:
        clip_dir = os.path.join( self._video_dir(), clip_name )
        if not os.path.isdir( clip_dir ):
            return None
        mp4_paths = sorted(
            os.path.join( clip_dir, entry )
            for entry in os.listdir( clip_dir )
            if entry.lower().endswith( '.mp4' )
        )
        return mp4_paths[ 0 ] if mp4_paths else None

    def live_frame_iter( self, clip_name : str, count : int ):
        """Yield ``count`` JPEG byte-frames starting at the current wall-clock
        index, looping through the clip — a bounded live-feed window for the
        ZoneMinder MJPEG stream. Yields nothing when synthetic / missing /
        empty. Lazy (one frame read at a time), so it never holds the whole
        clip in memory."""
        frames = self._selectable_frames( clip_name )
        if not frames:
            return
        start = int( time.monotonic() * self.VIDEO_FPS ) % len( frames )
        for offset in range( count ):
            data = self._read_frame( frames[ ( start + offset ) % len( frames ) ] )
            if data is not None:
                yield data
            continue
        return

    def clip_frame_iter( self, clip_name : str ):
        """Yield every frame of the clip once, in order (lazy) — for event
        playback, which plays the whole event clip. Yields nothing when
        synthetic / missing / empty."""
        for path in self._selectable_frames( clip_name ):
            data = self._read_frame( path )
            if data is not None:
                yield data
            continue
        return

    def _selectable_frames( self, clip_name : str ) -> List[ str ]:
        if not clip_name or clip_name == SYNTHETIC_CLIP_VALUE:
            return []
        if clip_name not in self._frames_by_clip:
            self._frames_by_clip[ clip_name ] = self._scan_clip_frames( clip_name )
        return self._frames_by_clip[ clip_name ]

    def _scan_clip_names( self ) -> List[ str ]:
        video_dir = self._video_dir()
        if not video_dir or not os.path.isdir( video_dir ):
            return []
        names = [
            entry for entry in os.listdir( video_dir )
            if os.path.isdir( os.path.join( video_dir, entry ))
        ]
        names.sort()
        return names

    def _scan_clip_frames( self, clip_name : str ) -> List[ str ]:
        clip_dir = os.path.join( self._video_dir(), clip_name )
        if not os.path.isdir( clip_dir ):
            return []
        frames = [
            os.path.join( clip_dir, entry )
            for entry in os.listdir( clip_dir )
            if entry.lower().endswith( self._JPEG_EXTENSIONS )
        ]
        frames.sort()
        return frames

    def _read_frame( self, path : str ) -> Optional[ bytes ]:
        try:
            with open( path, 'rb' ) as frame_file:
                return frame_file.read()
        except OSError:
            logger.warning( 'Failed to read clip frame: %s', path )
            return None

    def _video_dir( self ) -> str:
        return getattr( settings, 'SIMULATOR_VIDEO_DIR', '' ) or ''
