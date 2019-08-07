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
import glob
import os
import datetime
import logging

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
        ssid = subprocess.check_output("iwgetid -r".split()).decode('utf-8')
        cfg = subprocess.check_output("ifconfig wlan0".split()).decode('utf-8')
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
    
def bluez_available():
    try:
        import dbus.mainloop.glib
        import dbus
        import dbus.service
        try:
          from gi.repository import GObject
        except ImportError:
          import gobject as GObject
        return True
    except ImportError:
        return False
    
    return False
