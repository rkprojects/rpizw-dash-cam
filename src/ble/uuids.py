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

# Custom 128 bit UUID Base. All remaining Custom IDs derived from it.
CUSTOM_UUID_BASE = '1912869a-8d28-4827-a571-6b0a491ea841'

# Bluetooth SIG UUID Base.
BLUETOOTH_UUID_BASE = '00000000-0000-1000-8000-00805F9B34FB'

def to128bit_custom(uuid_16bit):
    return CUSTOM_UUID_BASE[0:4] + str(uuid_16bit) + CUSTOM_UUID_BASE[8:]

def to128bit_ble(uuid_16bit):
    return BLUETOOTH_UUID_BASE[0:4] + str(uuid_16bit) + BLUETOOTH_UUID_BASE[8:]



