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

# Implements Bluetooth SIG - Location and Speed  Characteristic Value
# parser.

import struct 
import util

"""
Builder functions return their data length for next
running offset.

Each builder function parses data as per :
https://www.bluetooth.com/wp-content/uploads/Sitecore-Media-Library/Gatt/Xml/Characteristics/org.bluetooth.characteristic.location_and_speed.xml
"""


# TODO Test precision due to rounding/float conversion 

def _build_ispeed(obj, flags, data):
    obj.ispeed = util.unpack_uint16(data, 10**-2, 2)
    return 2
    
def _build_total_distance(obj, flags, data):
    obj.total_distance = util.unpack_uint24(data, 10**-1, 1)
    return 3
    
def _build_location(obj, flags, data):
    obj.latitude = util.unpack_sint32(data, 10**-7, 7)
    obj.longitude = util.unpack_sint32(data[4:8], 10**-7, 7)
    return 8

def _build_elevation(obj, flags, data):
    obj.elevation = util.unpack_sint24(data, 10**-2, 2)
    return 3
    
def _build_heading(obj, flags, data):
    obj.heading = util.unpack_uint16(data, 10**-2, 2)
    return 2

def _build_rolling_time(obj, flags, data):
    obj.rolling_time = data[0]
    return 1

def _build_utc_time(obj, flags, data):
    obj.utc_time = util.unpack_ble_gatt_datetime(data)
    return 7

def _build_position_status(obj, flags):
    obj.position_status = (flags >> 7) & 0x3
    return 0
    
def _build_speed_dist_format(obj, flags):
    obj.speed_distance_fmt = (flags >> 9) & 0x1
    return 0

def _build_elevation_source(obj, flags):
    obj.elevation_source = (flags >> 10) & 0x3
    return 0

def _build_heading_source(obj, flags):
    obj.heading_source = (flags >> 12) & 0x1
    return 0

    
_builder_index = [
    #0: 
    _build_ispeed,
    #1: 
    _build_total_distance,
    #2: 
    _build_location,
    #3: 
    _build_elevation,
    #4: 
    _build_heading,
    #5: 
    _build_rolling_time,
    #6: 
    _build_utc_time,
    #7: 
    None,
    #8: 
    None,
    #9: 
    None,
    #10: 
    None,
    #11: 
    None,
    #12: 
    None,
    #13: 
    None,
    #14: 
    None,
    #15: 
    None
]

# _deg_sign = u'\N{DEGREE SIGN}'
        
class LocationSpeed():
    
    def __init__(self, data):
        flags = struct.unpack("<H", data[0:2])[0]
        self.flags = flags

        offset = 2
        for i in range(0,7):
            if (flags & (1<<i)) != 0:
                if _builder_index[i]:
                    offset += _builder_index[i](self, flags, data[offset:])
    
        _build_position_status(self, flags)
        _build_speed_dist_format(self, flags)
        _build_elevation_source(self, flags)
        _build_heading_source(self, flags)

    def is_location_present(self):
        return ((self.flags >> 2) & 0x1) == 1
     
    def is_speed_present(self):
        return (self.flags & 0x1) == 1
    
    def is_heading_present(self):
        return ((self.flags >> 4) & 0x1) == 1
        
    def __str__(self):
        s = ""
        if self.is_location_present():
            if len(s) > 0:
                s += ", "
            s += "Latitude: {} DD, Longitude: {} DD".format(self.latitude,
                                    self.longitude)
        
        if self.is_speed_present():
            # 1 m/s = 3.6 kmph
            speed = self.ispeed * 3.6
            if len(s) > 0:
                s += ", "
            s += "Speed: {} km/h".format(speed)
                
        if self.is_heading_present():
            if len(s) > 0:
                s += ", "
            s += " Heading: {} D".format(self.heading)
            
        return s
