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
