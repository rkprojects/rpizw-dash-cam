# Dash Camera with Raspberry Pi Zero W
# Copyright (C) 2019 Ravikiran Bukkasagara <contact@ravikiranb.com>
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

# Top level entry point for BLE Gatt Service and Advertisement registrations
# and running main event loop.
# For now the advertisement will stop after default timeout of 180 seconds.


import dbus.mainloop.glib

try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

import threading
import logging

import dcam_service
import dcam_advertisement

logger = logging.getLogger(__name__)

def start(control_cb=None):
    try:    
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        
        logger.info("Registering GATT Service")
        
        app = dcam_service.start(bus)
        # Setup all service callbacks before advertising.
        service = app.services[0]
        service.register_control_cb(control_cb)
        
        logger.info("Registering Advertisement")
        ad = dcam_advertisement.start(bus)
        mainloop = GObject.MainLoop()
        
        th_mainloop = threading.Thread(target=mainloop.run)
        th_mainloop.start()
        
        logger.info("DCam Service Online")
        
        return service
    except Exception as e:
        logger.error(e)
        return None


