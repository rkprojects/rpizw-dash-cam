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

# Entry point module for the program

import time
from datetime import datetime
import os
import sys
import logging
import util
import argparse
import queue
import traceback

import webinterface
import recorder
from command import Command
import config


parser = argparse.ArgumentParser()
parser.add_argument("-r", "--records-location", 
            help="Where to store recordings",
            default=config.RECORDS_LOCATION)
parser.add_argument("-L", "--loglevel", 
            help="Log level threshold",
            default="info")

args = parser.parse_args()

user_dir_error = (False, None)
try:
    d = os.path.abspath(args.records_location)
    if os.path.isdir(d):
        config.update_records_location(d)
    else:
        user_dir_error = (True, "Given records location is not a directory.")
except Exception as e:
    user_dir_error = (True, e)

# Log all events even if given arguments are incorrect as
# application is running in background.
# Log file location
LOG_FILE_PATH = (config.RECORDS_LOCATION 
                + '/' 
                + datetime.now().strftime("%Y-%m-%d")
                + '.log')
                
loglevel = logging.INFO
user_loglevel = getattr(logging, args.loglevel.upper(), None)
user_loglevel_invalid = False

if not isinstance(user_loglevel, int):
    user_loglevel_invalid = True
else:
    loglevel = user_loglevel

logging.basicConfig(format='%(module)s:%(lineno)s:%(levelname)s:%(message)s', 
        filename=LOG_FILE_PATH, 
        level=loglevel)

logger = logging.getLogger(__name__)

if user_dir_error[0]: 
    logger.error("Invalid given directory '%s'", args.records_location)
    if user_dir_error[1] is not None:
        logger.critical("Error: '%s'", user_dir_error[1])
        sys.exit(-1)
    logger.warning("Defaulting to '%s'.", config.RECORDS_LOCATION)
    
if user_loglevel_invalid:
    logger.error("Loglevel '%s' given is incorrect, defaulting to '%s'.", user_loglevel, loglevel)

util.delete_old_logs(config.RECORDS_LOCATION, config.KEEP_OLD_LOGS_FOR_DAYS)

# Global command queue
cmd_q = queue.Queue()


recorder.init()
logger.info("Starting Recording\n\n")
recorder.start()

webinterface.WebInterfaceHandler.cmd_q = cmd_q

logger.info("Starting Web Server\n\n")
web_th = webinterface.start()

# Enable BLE Control feature if BlueZ is available
ble_service = None
if util.bluez_available():
    sys.path.append(config.HOME + "/ble")
    import ble_dcam
    
    logger.info("Starting BLE GATT Server\n\n")
    ble_dcam.start(cmd_q)
else:
    logger.error("BLE feature won't be enabled: requirements not met.")

try:
    while True:
        request = cmd_q.get()
        if request.cmd == Command.CMD_REBOOT:
            recorder.stop()
            util.reboot()
            request.done()
        elif request.cmd == Command.CMD_SHUTDOWN:
            recorder.stop()
            util.shutdown()
            request.done()
        elif request.cmd == Command.CMD_STOP_REC:
            recorder.stop()
            request.done()
        elif request.cmd == Command.CMD_START_REC:
            recorder.start()
            request.done()
        elif request.cmd == Command.CMD_ROTATE:
            recorder.queue_commands(request)
        elif request.cmd == Command.CMD_TAKE_LIVE_SNAPSHOT:
            recorder.queue_commands(request)
        elif request.cmd == Command.CMD_SET_SYS_DATETIME:
            """
            Changing system time to forward and then backward (due 
            to NTP sync) may cause python parked 
            threads to block indefinitely. Leading the dashcam 
            to become unresponsive.
            https://bugs.python.org/issue23428
            """
            util.set_system_datetime(request.data)
            request.done()
        elif request.cmd == Command.CMD_ENABLE_GPS_LOCATION:
            # For design with on-board GPS source.
            # Activate that here.
            request.done()
        elif request.cmd == Command.CMD_SET_LOCATION_SPEED:
            recorder.queue_commands(request)

except Exception as e:
    logger.error(e)
    logger.error(traceback.format_exc())
finally:
    recorder.stop()
    web_th.join()

