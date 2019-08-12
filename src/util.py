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

import subprocess
import glob
import os
import datetime
import logging
import struct
import traceback

logger = logging.getLogger(__name__)

def get_cpu_temperature():
    temps = subprocess.check_output(['vcgencmd', 
                    'measure_temp']).decode('utf-8')
    if 'temp=' in temps:
        temps = temps.strip()
        tempv = temps.split('=')[1]
        return float(tempv.split("'")[0])
    
    return 0.0


def delete_old_logs(log_dir, days_to_keep=2):
    # Delete log files older than days_to_keep
    td = datetime.timedelta(days=days_to_keep)
    d = datetime.datetime.today() - td
    
    log_files = glob.glob(log_dir + '/*.log')
    for log_file in log_files:
            if os.path.getmtime(log_file) < d.timestamp():
                os.remove(log_file)
                logger.warning("Removing old log file: %s", log_file)

def get_wlan_info():
    # Return tuple (ssid, device_ip)
    try:
        ssid = subprocess.check_output("iwgetid -r".split()).decode('utf-8').strip()
        cfg = subprocess.check_output("ifconfig wlan0".split()).decode('utf-8').strip()
        i = cfg.find("inet ")
        ip = ""
        if i >= 0:
            ip = cfg[i:].split()[1]
    except Exception as e:
        logger.error("Failed to get WiFi connection details: %s", e)
        ssid = "-"
        ip = "-"
    finally:
        return (ssid, ip)

def reboot():
    os.system("sudo reboot")
    
def shutdown():
    os.system("sudo poweroff")

def set_system_datetime(dtime):
    os.system('sudo date -s "' + dtime.strftime("%Y-%m-%d %H:%M:%S") + '"') 
    
def bluez_available():
    try:
        # There could be multiple versions installed.
        # Check if running version of bluetoothd is >= 5.50
        btd_path = subprocess.check_output("ps -o cmd -C bluetoothd --no-headers".split()).decode('utf-8').strip()
        if len(btd_path) == 0:
            logger.info("Bluetoothd service required for BLE features.")
            return False
        
        btd_version = subprocess.check_output((btd_path + " -v").split()).decode('utf-8').strip()
        fields = btd_version.split('.')
        major = int(fields[0])
        minor = int(fields[1])
        logger.info("Found bluetoothd service version: {}, required: >= 5.50".format(btd_version))
        if major >= 5:
            if major == 5 and minor < 50:
                    return False
        else:
            return False
            
        import dbus.mainloop.glib
        import dbus
        import dbus.service
        try:
          from gi.repository import GObject
        except ImportError:
          import gobject as GObject
        return True
    except ImportError as e:
        logger.info("Required module for BLE service not found: {}".format(e))
        return False
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return False
    return False

def unpack_uint16(barray, exp=10**0, rnd_digits=2):
    v = struct.unpack("<H", barray[0:2])[0]
    return round(v * exp, rnd_digits)

def unpack_uint24(barray, exp=10**0, rnd_digits=2):
    v = struct.unpack("<I", barray[0:3] + bytes([0]))[0]
    return round(v * exp, rnd_digits)

def unpack_sint32(barray, exp=10**0, rnd_digits=2):
    v = struct.unpack("<i", barray[0:4])[0]
    return round(v * exp, rnd_digits)

def unpack_sint24(barray, exp=10**0, rnd_digits=2):
    sign = 0
    if (barray[2] & 0x80) != 0:
        sign = 0xff
        
    v = struct.unpack("<i", barray[0:3] + bytes([sign]))[0]
    return round(v * exp, rnd_digits)
    
def unpack_ble_gatt_datetime(barray):
    raw_dt = struct.unpack("<HBBBBB", barray[0:7])
    dt = datetime.datetime(raw_dt[0], # year 
                raw_dt[1], # mon
                raw_dt[2], # day
                hour=raw_dt[3],
                minute=raw_dt[4],
                second=raw_dt[5]
                )
    return dt

def pack_ble_gatt_datetime(dt):
    packed_dt = struct.pack('<H', dt.year) + bytes([dt.month,
                                            dt.day,
                                            dt.hour,
                                            dt.minute,
                                            dt.second])
                
    return packed_dt

       
    
