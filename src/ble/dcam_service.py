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

# Implements DashCam custom service and its characteristics. 
# All characteristics has a default Characteristic User Description Descriptor.
# Useful in Smartphone GATT Service explorer apps.

import struct
import dbus
import threading
import logging

from gatt_dbus_service import *

import uuids

logger = logging.getLogger(__name__)

DBUS_PATH_BASE = '/com/ravikiranb/rpizw_dcam'

SERVICE_PATH = DBUS_PATH_BASE + '/service0'


# Do not use '0x' prefix for hex IDs
DCAM_SERVICE_UUID         = uuids.to128bit_custom('0001')

GENERIC_BYTE_CHAR_UUID      = uuids.to128bit_custom('0100')

BLUETOOTH_STRING_CHAR_UUID  = uuids.to128bit_ble('2A3D')

IPADDR_CHAR_UUID            = BLUETOOTH_STRING_CHAR_UUID
RECORDING_STATUS_CHAR_UUID  = BLUETOOTH_STRING_CHAR_UUID
# Bluetooth SIG - Software Revision String
VERSION_CHAR_UUID           = uuids.to128bit_ble('2A28')
# Bluetooth SIG - Temperature Celsius
TEMPERATURE_CHAR_UUID       = uuids.to128bit_ble('2A1F')
REBOOT_CHAR_UUID            = BLUETOOTH_STRING_CHAR_UUID
STOP_RECORDING_CHAR_UUID    = BLUETOOTH_STRING_CHAR_UUID
# Bluetooth SIG - Date Time
SYSTEM_DATE_TIME_CHAR_UUID  = uuids.to128bit_ble('2A08')

# Bluetooth SIG - Characteristic User Description
CHAR_USER_DESCRIPTION_DESC_UUID = uuids.to128bit_ble('2901')

class DCamService(Service):
    """
    This service will update remote client about:
    1. Assigned IP Address on WiFi (Notify)
    2. Recording Status (Notify)
    3. Version (Read Only)
    4. Temperature deg-Celsius (Notify)

    Controls: Needs authenticated connection.
    1. Control Flag (authenticated-signed-writes)
        a. bit 0 = Reboot
        b. bit 1 = Shutdown
        c. bit 2 = Stop Recording
        d. bit 3 = Start Recording
        e. bit 4 = Disable Advertisement
        f. bit 5-7 = Set to zero.
    # TODO
    2. Date Time (read, authenticated-signed-writes)
    3. Location (authenticated-signed-writes)
    """
    def __init__(self, bus):
        Service.__init__(self, bus, SERVICE_PATH, DCAM_SERVICE_UUID, True)
        
        self.ipaddr_char = TextReadNotifyChar(bus, 0, self, "WiFi SSID - IP Address")
        self.recording_status_char = TextReadNotifyChar(bus, 1, self, "Recording Status")
        self.version_char = VersionChar(bus, 2, self)
        self.temperature_char = TemperatureChar(bus, 3, self, "SoC Temperature")
        
        self.add_characteristic(self.ipaddr_char)
        self.add_characteristic(self.recording_status_char)
        self.add_characteristic(self.version_char)
        self.add_characteristic(self.temperature_char)
        
        self.control_char = ByteWriteChrc(bus, 4, self, "Control Settings")
        
        self.add_characteristic(self.control_char)
        

    def update_ipaddr(self, value):
        self.ipaddr_char.update(value)
    
    def update_temperature(self, value):
        self.temperature_char.update(value)
    
    def update_version(self, value):
        self.version_char.update(value)
        
    def update_recording_status(self, value):
        self.recording_status_char.update(value)
        
    def register_control_cb(self, cb):
        self.control_char.update_cb(cb)
        

class TemperatureChar(Characteristic):
    def __init__(self, bus, index, service, description=None):
        Characteristic.__init__(
                self, bus, index,
                TEMPERATURE_CHAR_UUID,
                ['read', 'notify'],
                service)
        self.notifying = False
        self._current_temp = dbus.Array([0,0], signature='y')
        if description:
            self.add_descriptor(
                CharacteristicUserDescriptionDescriptor(bus, 0, self, description))

    """
    Temperature value should be signed 16 bit integer.
    """
    def update(self, new_value):
        if new_value is not None:
            self._current_temp = dbus.Array(struct.pack('<h', new_value), signature='y')

        if not self.notifying:
            return self.notifying

        logger.info('Updating value: ' + repr(self._current_temp))

        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': self._current_temp }, [])

        return self.notifying

    def StartNotify(self):
        if self.notifying:
            logger.info('Already notifying, nothing to do')
            return

        self.notifying = True
        self.update(None)

    def StopNotify(self):
        if not self.notifying:
            logger.info('Not notifying, nothing to do')
            return

        self.notifying = False
    
    def ReadValue(self, options):
        return self._current_temp

class TextReadNotifyChar(Characteristic):
    def __init__(self, bus, index, service, description=None):
        Characteristic.__init__(
                self, bus, index,
                BLUETOOTH_STRING_CHAR_UUID,
                ['read', 'notify'],
                service)
        self.notifying = False
        self._text = bytes("na", encoding='utf-8')
        if description:
            self.add_descriptor(
                CharacteristicUserDescriptionDescriptor(bus, 0, self, description))

    def ReadValue(self, options):
        return self._text

    def update(self, new_value):
        if new_value is not None:
            self._text = bytes(new_value, encoding='utf-8')

        if not self.notifying:
            return self.notifying

        logger.info('Updating value: ' + repr(self._text))

        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': self._text }, [])

        return self.notifying

    def StartNotify(self):
        if self.notifying:
            logger.info('Already notifying, nothing to do')
            return

        self.notifying = True
        self.update(None)

    def StopNotify(self):
        if not self.notifying:
            logger.info('Not notifying, nothing to do')
            return

        self.notifying = False


class VersionChar(Characteristic):
    def __init__(self, bus, index, service, description=None):
        Characteristic.__init__(
                self, bus, index,
                VERSION_CHAR_UUID,
                ['read'],
                service)
        self._version = bytes("Not Available", encoding='utf-8')
        if description:
            self.add_descriptor(
                CharacteristicUserDescriptionDescriptor(bus, 0, self, description))
                
    def update(self, new_value):
        self._version = bytes(new_value, encoding='utf-8')
        return False   
    
    def ReadValue(self, options):
        return self._version
        
class ByteWriteChrc(Characteristic):
    
    def __init__(self, bus, index, service, description=None, on_write_cb=None):
        Characteristic.__init__(
                self, bus, index,
                GENERIC_BYTE_CHAR_UUID,
                ['write'],
                service)
        if description:
            self.add_descriptor(
                CharacteristicUserDescriptionDescriptor(bus, 0, self, description))
        
        self.on_write_cb = on_write_cb
        
    def update_cb(self, cb):
        self.on_write_cb = cb
            
    def WriteValue(self, value, options):
        logger.info('ByteWriteChrc WriteValue called')

        if len(value) != 1:
            raise InvalidValueLengthException()

        byte = value[0]
        
        if self.on_write_cb:
            threading.Thread(target=self.on_write_cb, args=(byte,)).start()
        

class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Read only User descriptions, useful while using gatt tools on remote side.
    """
    def __init__(self, bus, index, characteristic, description):
        self.writable = False
        self.value = bytes(description, encoding='utf-8')
        Descriptor.__init__(
                self, bus, index,
                CHAR_USER_DESCRIPTION_DESC_UUID,
                ['read'],
                characteristic)

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        raise NotPermittedException()


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(DCamService(bus))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        logger.info('GetManagedObjects')

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response

manager = None

def start(bus):
    global manager

    adapter = find_adapter(bus)
    if not adapter:
        logger.info('GattManager1 interface not found')
        return

    manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter),
            GATT_MANAGER_IFACE)

    app = Application(bus)

    logger.info('Registering GATT application...')

    manager.RegisterApplication(app.get_path(), {},
                                    reply_handler=_register_cb,
                                    error_handler=_register_error_cb)

    return app

def stop(app):
    global manager
    if manager is not None:
        logger.info('GATT application un-registered')
        manager.UnregisterApplication(app.get_path())

def _register_cb():
    logger.info('GATT application registered')


def _register_error_cb(error):
    logger.error('Failed to register application: ' + str(error))

