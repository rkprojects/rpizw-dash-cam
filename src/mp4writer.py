# Dash Camera with Raspberry Pi Zero W
# Copyright (C) 2019 Ravikiran Bukkasagara <code@ravikiranb.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# TAB = 4 spaces

import subprocess
import threading
import queue
import traceback
import logging
import io
import shutil

logger = logging.getLogger(__name__)

class MP4Writer:
    # Converts h264 video from camera to mp4 format with ffmpeg on the
    # fly. Class instance can be passed as argument where file object
    # is expected.
    
    MAX_QUEUE_SIZE = 50
    # Video buffer size to hold before commiting to queue.
    MAX_VIDEO_BIO_SIZE = 1*1024*1024
    
    def __init__(self, filepath="o.mp4", fps=30, 
                input_format="h264", codec="copy"):
        self._filepath = filepath
        self._fps = fps
        self._iformat = input_format
        self._codec = codec
        
        # For fast playback in browser use option -movflags faststart.
        # Write input to process stdin.
        ffmpeg_cmd = """ffmpeg -v 16 -framerate {0} -f {1}
                    -i pipe:0 -codec {2} -movflags faststart
                    -y -f mp4 {3}""".format(
                        self._fps,
                        self._iformat,
                        self._codec,
                        self._filepath)
        
        self._proc = subprocess.Popen(ffmpeg_cmd.split(), 
                                stdin=subprocess.PIPE)
                                
        self._video_q = queue.Queue(MP4Writer.MAX_QUEUE_SIZE)
        self._video_bio_size = 0
        self._video_bio = io.BytesIO()
        
        self._th = threading.Thread(target=self.write_to_proc)
        self._th.daemon = True
        self._th.start()
        
    def write(self, vdata):
        # Passing process stdin directly to picamera causes frame
        # drop in full-hd 30 fps format even with large buffer size
        # in the beginning few seconds. This is an alternative 
        # implementation to queue frames until subprocess 
        # catches up. If MAX_QUEUE_SIZE is also not sufficient then
        # frames will be dropped.
        
        # Buffered IO consumes all given data.
        self._video_bio.write(vdata)
        self._video_bio_size += len(vdata)
        
        if self._video_bio_size >= MP4Writer.MAX_VIDEO_BIO_SIZE:
            self._video_q.put(self._video_bio)
            self._video_bio = io.BytesIO()
            self._video_bio_size = 0
            
    def flush(self):
        if self._video_bio_size > 0:
            self._video_q.put(self._video_bio)
            self._video_bio = io.BytesIO()
            self._video_bio_size = 0
            
    def get_file_object(self):
        # If using underlying stdin file object directly then do 
        # not pass this instance as file object.  
        return self._proc.stdin
            
    def close(self):
        # Call this function to close writer thread 
        # even if process stdin was directly used outside.
        self.flush()
        self._video_bio.close()
        self._video_bio_size = 0
        self._video_q.put(None)
        self._th.join()
            
    def write_to_proc(self):
        while True:
            try:
                bio = self._video_q.get()
                if bio is None:
                    break
                bio.seek(0)
                shutil.copyfileobj(bio, self._proc.stdin)
                bio.close()
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(e)
                break
                            
        self._proc.stdin.flush()
        # does close internally calls flush?
        self._proc.stdin.close()
        self._proc.wait()
