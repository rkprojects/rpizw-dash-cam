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

import os

SOFTWARE_VERSION = "1.3.1"

HOME = os.getcwd()

# ----------- Compile time configurable parameters BEGIN --------
# Default location to store video recordings.
RECORDS_LOCATION = HOME + "/records"

# Maximum duration of each video in seconds. Change it as per use case.
DURATION_SEC = 60

# Limit and note maximum files to record when used disk space reaches 
# this value. Change it as per use case, leave enough free space for OS.
MAX_USED_DISK_SPACE_PERCENT = 70

# Video parameters. Change it as per use case. 
# Refer to picamera docs for valid values.
# https://picamera.readthedocs.io
VIDEO_FPS = 30
HIGH_RES_VIDEO_WIDTH = 1920
HIGH_RES_VIDEO_HEIGHT = 1080
VIDEO_QUALITY = 23

# Alternate video resolution to drop temperature.
LOW_RES_VIDEO_WIDTH = 1280
LOW_RES_VIDEO_HEIGHT = 720

# Size of text that will appear on top of recorded video.
ANNOTATE_TEXT_SIZE = 20

# How many days to keep old log files
KEEP_OLD_LOGS_FOR_DAYS = 2

# Reduce resolution when temperature exceeds threshold.
TEMPERATURE_THRESHOLD_HIGH = 75.0 # degree Celsius
# Restore high resolution when temperature drops.
TEMPERATURE_THRESHOLD_NORMAL = 60.0 # degree Celsius

HTTP_SERVER_PORT_NUMBER = 8080

# ---------- Compile time configurable parameters END-----------

LIVESNAP_FILENAME = "live_snap.jpg"
LIVESNAP_FILE = RECORDS_LOCATION + '/' + LIVESNAP_FILENAME

# Runtime settings (saved as dictionary) are stored in json format. 
CFG_FILENAME = "cfg.json"
CFG_FILE = RECORDS_LOCATION + '/' + CFG_FILENAME

RECORD_FORMAT_EXTENSION = ".mp4"

def update_records_location(loc):
    global RECORDS_LOCATION
    global LIVESNAP_FILE
    global CFG_FILE
    
    RECORDS_LOCATION = loc
    CFG_FILE = RECORDS_LOCATION + '/' + CFG_FILENAME
    LIVESNAP_FILE = RECORDS_LOCATION + '/' + LIVESNAP_FILENAME

