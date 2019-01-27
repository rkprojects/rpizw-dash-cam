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

import threading
import time


class WebCommandSync:
    # Synchronize a command between web interface and recorder.
    # For dash camera kind of use case there will be only one web user
    # at a time but for general purpose loop recording use case there 
    # might be multiple users accessing web interface simultaneously. 
    # If multiple requests for the same command occurs simultaneously
    # then all requests would be merged in to one.
    
    IDLE = 0
    REQUESTED = 1
    
    def __init__(self):
        self._state = WebCommandSync.IDLE
        self._lock = threading.Lock()
        self._event = threading.Event()
        
        # Command might include result, currently not used.
        self._context = None
    
    def start(self):
        # Called from web interface side.
        with self._lock:
            # Merge simultaneous commands.
            if self._state != WebCommandSync.REQUESTED:
                self._state = WebCommandSync.REQUESTED
    
    
    def requested(self):
        # Called from recorder side.
        with self._lock:
            if self._state == WebCommandSync.REQUESTED:
                return True
        return False
            
    def done(self, context=None):
        # Called from recorder side.
        with self._lock:
            self._state = WebCommandSync.IDLE       
            self._context = context
            # Give a event pulse to waiting threads.
            self._event.set()
            self._event.clear()

    def wait(self, timeout_seconds=5):
        # Called from web interface side.
        return self._event.wait(timeout_seconds)
