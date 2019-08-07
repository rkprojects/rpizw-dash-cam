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

# Extends LEAdvertisement base class for DashCam specific custom service.

from dbus_advertisement import *
import dbus.service
import logging

import dcam_service

logger = logging.getLogger(__name__)

ADVERTISEMENT_PATH = dcam_service.DBUS_PATH_BASE + '/advertisement'

class DCamAdvertisement(Advertisement):

    def __init__(self, bus):
        Advertisement.__init__(self, bus, ADVERTISEMENT_PATH, 'peripheral')
        self.add_service_uuid(dcam_service.DCAM_SERVICE_UUID)
        self.add_manufacturer_data(0xffff, [0x0])
        self.add_local_name('RPi DashCam')
        self.include_tx_power = True
        
manager = None

def start(bus):
    global manager

    adapter = find_adapter(bus)
    if not adapter:
        logger.info('LEAdvertisingManager1 interface not found')
        return

    adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                   DBUS_PROP_IFACE)

    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                LE_ADVERTISING_MANAGER_IFACE)

    adv = DCamAdvertisement(bus)

    manager.RegisterAdvertisement(adv.get_path(), {},
                                     reply_handler=_register_cb,
                                     error_handler=_register_error_cb)
    return adv

def stop(adv):
    global manager

    if manager is not None:
        logger.info('Advertisement un-registered')
        manager.UnregisterAdvertisement(adv.get_path())
        


def _register_cb():
    logger.info('Advertisement registered')


def _register_error_cb(error):
    logger.error('Failed to register advertisement: ' + str(error))

