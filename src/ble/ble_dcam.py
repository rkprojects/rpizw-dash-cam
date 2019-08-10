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
import traceback

import dcam_service
import dcam_advertisement

import config
import recorder
from command import Command

logger = logging.getLogger(__name__)

_ble_service = None

_ble_cmd_to_glb_cmd = {
    dcam_service.CTRL_CMD_REBOOT: Command.CMD_REBOOT,
    dcam_service.CTRL_CMD_SHUTDOWN: Command.CMD_SHUTDOWN,
    dcam_service.CTRL_CMD_START_REC: Command.CMD_START_REC,
    dcam_service.CTRL_CMD_STOP_REC: Command.CMD_STOP_REC,
    dcam_service.CTRL_CMD_ENABLE_GPS_LOC: Command.CMD_ENABLE_GPS_LOCATION
}

def _on_cpu_temp(v):
    global _ble_service
    
    # Temperature Charactertistics expects short int with exponent 10^-1
    _ble_service.update_temperature(int(v * 10))

def _control_cb(v):
    pass
    
def start(cmd_q):
    global _ble_service
    try:    
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        
        logger.info("Registering GATT Service")
        
        app = dcam_service.start(bus)
        # Setup all service callbacks before advertising.
        _ble_service = app.services[0]
        _ble_service.register_control_cb(lambda v: cmd_q.put(Command(_ble_cmd_to_glb_cmd[v])) if v in _ble_cmd_to_glb_cmd else None)
        _ble_service.register_sys_datetime_cb(lambda v: cmd_q.put(Command(Command.CMD_SET_SYS_DATETIME, v)))
        _ble_service.register_location_speed_cb(lambda v: cmd_q.put(Command(Command.CMD_SET_LOCATION_SPEED, v)))

        logger.info("Registering Advertisement")
        ad = dcam_advertisement.start(bus)
        mainloop = GObject.MainLoop()
        
        th_mainloop = threading.Thread(target=mainloop.run)
        th_mainloop.start()
        
        logger.info("DCam Service Online")
        
        _ble_service.update_version(config.SOFTWARE_VERSION)
        recorder.subscribe_for_cpu_temp(lambda v: _ble_service.update_temperature(int(v * 10)))
        recorder.subscribe_for_status(lambda v: _ble_service.update_recording_status(v))
        
        return _ble_service
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return None


