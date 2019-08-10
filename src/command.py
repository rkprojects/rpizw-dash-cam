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

class Command:
    CMD_STOP_REC            = 1
    CMD_START_REC           = 2
    CMD_REBOOT              = 3
    CMD_SHUTDOWN            = 4
    # data = rotation value
    CMD_ROTATE              = 5
    CMD_TAKE_LIVE_SNAPSHOT  = 6
    # data = DateTime object
    CMD_SET_SYS_DATETIME    = 7
    # data = (Latitude, Longitude)
    CMD_ENABLE_GPS_LOCATION = 8
    # data = LocationSpeed from ble
    CMD_SET_LOCATION_SPEED  = 9
    
    # Created by sender.
    def __init__(self, cmd, data=None):
        self.cmd = cmd
        # Type based on command
        self.data = data
        self._event = threading.Event()
        
    # Called from receiver's side.
    def done(self):
        self._event.set()

    # Called sender's side.
    def wait(self, timeout_seconds=5):
        return self._event.wait(timeout_seconds)
            
