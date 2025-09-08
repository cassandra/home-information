"""
Event
======
Each Event will hold a single ZoneMinder Event.
It is basically a bunch of getters for each access to event data.
If you don't see a specific getter, just use the generic get function to get
the full object
"""

from .Base import Base
# import progressbar as pb  # Removed dependency - progress bars not needed
import requests
import os
from . import globals as g


class Event(Base):
    def __init__(self, event=None, api=None):
        self.event = event
        self.api = api
               
    def get(self):
        """Returns event object.

        Returns:
            :class:`pyzm.helpers.Event`: Event object
        """
        return self.event['Event']
    
    def get_image_url(self, fid='snapshot'):
        """Returns the image URL for the specified frame
        
        Args:
            fid (str, optional): Default frame identification. Defaults to 'snapshot'.
        
        Returns:
            string: URL for the image
        """        
        eid = self.id()
        url = self.api.portal_url + '/index.php?view=image&eid={}&fid={}'.format(eid, fid) + '&' + self.api.get_auth()
        return url

    def get_video_url(self):
        """Returms the video URL for the specified event
        
        Returns:
            string: URL for the video file
        """        
        if not self.video_file():
            g.logger.Error('Event {} does not have a video file'.format(self.id()))
            return None
        eid = self.id()
        url = self.api.portal_url + '/index.php?mode=mpeg&eid={}&view=view_video'.format(eid) + '&' + self.api.get_auth()
        return url
    
    def download_image(self, fid='snapshot', dir='.', show_progress=False):

        """Downloads an image frame of the current event object
        
        Args:
            fid (str, optional): Frame ID. Defaults to 'snapshot'.
            dir (str, optional): Path to save the image to. Defaults to '.'.
            show_progress (bool, optional): If enabled shows a progress bar (if possible). Defaults to False.
        
        Returns:
            string: path+filename of downloaded image
        
        """

        url = self.get_image_url(fid)
        f = self._download_file(url, str(self.id()) + '-' + fid + '.jpg', dir, show_progress)
        g.logger.Info('File downloaded to {}'.format(f))
        return f

    def download_video(self, dir='.', show_progress=False):
        """Downloads a video mp4 of the current event object
        Only works if there an actual video 
        
        Args:
            dir (str, optional): Path to save the image to. Defaults to '.'.
            show_progress (bool, optional): If enabled shows a progress bar (if possible). Defaults to False.
        
        Returns:
            string: path+filename of downloaded video
        
        """           
           
        url = self.get_video_url()
        if not url:
            return None
        f = self._download_file(url, str(self.id()) + '-video' + '.mp4', dir, show_progress)
        g.logger.Info('File downloaded to {}'.format(f))
        return f

    def delete(self):
        """Deletes this event

        Returns:
            json: API response
        """
        url = self.api.api_url + '/events/{}.json'.format(self.id())
        return self.api._make_request(url=url, type='delete')

    def monitor_id(self):
        """returns monitor ID of event object.

        Returns:
            int: monitor id
        """
        return int(self.event['Event']['MonitorId'])
    
    def id(self):
        """returns event id of event.

        Returns:
            int: event id
        """
        return int(self.event['Event']['Id'])

    def name(self):
        """returns name of event.

        Returns:
            string: name of event
        """      
        return self.event['Event']['Name'] or None
    
    def video_file(self):
        """returns name of video file in which the event was stored.

        Returns:
            string: name of video file
        """
        return self.event['Event'].get('DefaultVideo')
    
    def cause(self):
        """returns event cause.

        Returns:
            string: event cause
        """ 
        return self.event['Event']['Cause'] or None
    
    def notes(self):
        """returns event notes.

        Returns:
            string: event notes
        """
        return self.event['Event']['Notes'] or None
    
    def fspath(self):
        """returns the filesystem path where the event is stored. Only
        available in ZM 1.33+

        Returns:
            string: path
        """
        return self.event['Event'].get('FileSystemPath')
    
    def duration(self):
        """Returns duration of event in seconds.

        Returns:
            float: duration
        """
        return float(self.event['Event']['Length'])
    
    def total_frames(self):
        """Returns total frames in event.

        Returns:
            int: total frames
        """
        return int(self.event['Event']['Frames'])
    
    def alarmed_frames(self):
        """Returns total alarmed frames in event.

        Returns:
            int: total alarmed frames
        """
        return int(self.event['Event']['AlarmFrames'])
    
    def score(self):
        """Returns total, average and max scores of event.

        Returns:
            dict: As below::

            {
                'total': float,
                'average': float,
                'max': float
            }
        """
        return {
            'total': float(self.event['Event']['TotScore']),
            'average': float(self.event['Event']['AvgScore']),
            'max': float(self.event['Event']['MaxScore'])
        }
    
    def _download_file(self, url, file_name, dest_dir, show_progress=False, reauth=True):
        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        full_path_to_file = dest_dir + os.path.sep + file_name

        if os.path.exists(dest_dir + os.path.sep + file_name):
            return full_path_to_file

        g.logger.Info("Downloading " + file_name + " from " + url)

        try:
            req = requests
            if self.api and self.api.get_session():
                req = self.api.get_session()
                # print ("OVERRIDING")
            r = req.get(url, allow_redirects=True, stream=True)

            # r = requests.get(url, allow_redirects=True, stream=True)
        except requests.exceptions.HTTPError as err:
            g.logger.Debug(1, 'Got download access error: {}'.format(err), 'error')
            if err.response.status_code == 401 and reauth:
                g.logger.Debug(1, 'Retrying login once')
                self._relogin()
                g.logger.Debug(1, 'Retrying failed request again...')
                return self._download_file(url, file_name, dest_dir, show_progress, reauth=False)
            else:
                raise err
        except Exception:
            # e = sys.exc_info()[0]
            # print(e)
            g.logger.Error("Could not establish connection. Download failed")
            return None

        if r.headers.get('Content-Type') and "text/html" in r.headers.get('Content-Type'):
            if reauth:
                g.logger.Error('We got redirected to login while trying to download, trying one more time')
                return self._download_file(url, file_name, dest_dir, show_progress, reauth=False)
            else:
                g.logger.Error('Failed doing reauth, not trying again')
                return None
        
        chunk_size = 1024

        if show_progress:
            g.logger.WarningG("Progress bar feature disabled in pyzm_client - progressbar dependency removed")
            # Progress bar removed - not needed for our use case
            # if r.headers.get('Content-Length'):
            #     file_size = int(r.headers['Content-Length'])
            #     if file_size:
            #         num_bars = round(file_size / chunk_size)
            #         bar = pb.ProgressBar(maxval=num_bars).start()
            #     else:
            #         bar = pb.ProgressBar().start()
        
        if r.status_code != requests.codes.ok:
            g.logger.Error("Error occurred while downloading file")
            return None

        count = 0
        
        with open(full_path_to_file, 'wb') as fp:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fp.write(chunk)
                if show_progress:
                    # bar.update(count)  # Progress bar disabled
                    count += 1
            fp.close()

        return full_path_to_file
