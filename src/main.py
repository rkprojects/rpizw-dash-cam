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

import socket
import time
import picamera
from datetime import datetime
import json
import os
import subprocess
import glob
import sys
import logging
import webinterface
import mp4writer
import util
import argparse

HOME = os.getcwd()

# ----------- Compile time configurable parameters BEGIN --------
# Default location to store video recordings.
RECORDS_LOCATION = HOME + '/records'

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
TEMPERATURE_THRESHOLD_NORMAL = 65.0 # degree Celsius

# ---------- Compile time configurable parameters END-----------


# Dictionary keys used in runtime configuration settings.
# Rotation (degrees) to apply to the camera.
CFG_ROT_KEY = 'rotation'

# Index number of the current recording. Post reboot/power cycle
# this number will be incremented before use.
CFG_CURR_INDEX_KEY = 'cindex'

# Loop when index number exceeds maximum files. Maximum number of 
# files/recordings to limit is calculated based on how much 
# disk space to use.
CFG_MAX_FILES_KEY = 'max-files'

# Number of times recordings have looped since the program was 
# installed. This can provide an approximation on the 
# sd card life expectancy.
CFG_N_LOOPS_KEY = 'n-loops'

# Dictionary to save configuration settings.
CFG = { 
    CFG_ROT_KEY: 0,
    CFG_CURR_INDEX_KEY: 0,
    CFG_MAX_FILES_KEY:0,
    CFG_N_LOOPS_KEY: 0
}

KB = 1024
MB = KB * KB
RECORD_FORMAT_EXTENSION = ".mp4"

def cfg_save():
    with open(CFG_FILE, 'w') as f:
        json.dump(CFG, f)

        
def get_disk_space_info():
    params = None
    try:
        # get disk space info of the "filesystem" where recordings 
        # are stored, in case multiple storage options are available in
        # future.
        op = subprocess.check_output(['df',
                        RECORDS_LOCATION]).decode('utf-8').split('\n')
        params = op[1].split()                
        params[4] = int(params[4].strip('%')) # Percent used
        # params[1] = int(params[1]) * KB # Disk Size - bytes
        # params[2] = int(params[2]) * KB # Used size - bytes
        # params[3] = int(params[3]) * KB # Available size - bytes
        # return (params[1], params[2], params[3], params[4])
        return params[4]
    except Exception as e:
        logger.error(e)
        return None



parser = argparse.ArgumentParser()
parser.add_argument("-r", "--records-location", 
            help="Where to store recordings",
            default=RECORDS_LOCATION)
parser.add_argument("-L", "--loglevel", 
            help="Log level threshold",
            default="info")

args = parser.parse_args()

user_dir_error = (False, None)
try:
    d = os.path.abspath(args.records_location)
    if os.path.isdir(d):
        RECORDS_LOCATION = d
    else:
        user_dir_error = (True, "Given records location is not a directory.")
except Exception as e:
    user_dir_error = (True, e)

# Log all events even if given arguments are incorrect as
# application is running in background.
# Log file location
LOG_FILE_PATH = (RECORDS_LOCATION 
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
    logger.warning("Defaulting to '%s'.", RECORDS_LOCATION)
    
if user_loglevel_invalid:
    logger.error("Loglevel '%s' given is incorrect, defaulting to '%s'.", user_loglevel, loglevel)

util.delete_old_logs(RECORDS_LOCATION, KEEP_OLD_LOGS_FOR_DAYS)

# Runtime settings (saved as dictionary) are stored in json format. 
CFG_FILE = RECORDS_LOCATION + '/cfg.json'

# Load existing configuration file or start fresh.
if os.path.exists(CFG_FILE):
    with open(CFG_FILE, 'r') as f:
        CFG = json.load(f)

logger.info("Starting web server\n\n")
webinterface.HOME = HOME
webinterface.RECORDS_LOCATION = RECORDS_LOCATION
webinterface.RECORD_FORMAT_EXTENSION = RECORD_FORMAT_EXTENSION
LIVESNAP_LOCATION = RECORDS_LOCATION + '/' + webinterface.LIVESNAP_NAME
webinterface.WebInterfaceHandler.program_start_time = datetime.now()
web_th = webinterface.start()

VIDEO_WIDTH = HIGH_RES_VIDEO_WIDTH
VIDEO_HEIGHT = HIGH_RES_VIDEO_HEIGHT

init_status = "Initializing Pi Camera to {0}x{1} @ {2} fps".format(
                VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS)
logger.info(init_status)
webinterface.WebInterfaceHandler.status_text = init_status

# Initialize camera
camera = picamera.PiCamera()
camera.resolution = (VIDEO_WIDTH, VIDEO_HEIGHT)
camera.framerate_range = (1, VIDEO_FPS)
camera.framerate = VIDEO_FPS
camera.annotate_background = True
fixed_annotation =  "RavikiranB.com"
camera.annotate_text_size = ANNOTATE_TEXT_SIZE
current_rotation = CFG[CFG_ROT_KEY]
camera.rotation = current_rotation

try:
    index = CFG[CFG_CURR_INDEX_KEY] + 1
    n_loops = CFG[CFG_N_LOOPS_KEY]
    webinterface.WebInterfaceHandler.status_text = "Starting Recording."
    webinterface.WebInterfaceHandler.program_start_time = datetime.now()
    high_temp_triggered = False
    
    while True:
        try:        
            disk_used_space_percent = get_disk_space_info()
                
            if CFG[CFG_MAX_FILES_KEY] == 0:
                if (disk_used_space_percent >= 
                        MAX_USED_DISK_SPACE_PERCENT):
                    # From now on recording index will loop 
                    # back to zero when index 
                    # reaches CFG[CFG_MAX_FILES_KEY]
                    CFG[CFG_MAX_FILES_KEY] = index
                    index = 0
                    n_loops += 1
                    CFG[CFG_N_LOOPS_KEY] = n_loops
            elif index >= CFG[CFG_MAX_FILES_KEY]:
                index = 0
                n_loops += 1
                CFG[CFG_N_LOOPS_KEY] = n_loops
                    
            # Update SoC temperature in video annotation, to keep 
            # track of resolution drop vs temp.
            cpu_temp = util.get_cpu_temperature()
            if cpu_temp >= TEMPERATURE_THRESHOLD_HIGH:
                if not high_temp_triggered:
                    logger.warning("CPU temperature %s C exceeded threshold %s C",
                                    cpu_temp, TEMPERATURE_THRESHOLD_HIGH)
                    logger.warning("Reducing video resolution")
                    VIDEO_WIDTH = LOW_RES_VIDEO_WIDTH
                    VIDEO_HEIGHT = LOW_RES_VIDEO_HEIGHT
                    camera.resolution = (VIDEO_WIDTH, VIDEO_HEIGHT)
                    high_temp_triggered = True
            elif cpu_temp <= TEMPERATURE_THRESHOLD_NORMAL:
                if high_temp_triggered:
                    logger.warning("Restoring high video resolution")
                    VIDEO_WIDTH = HIGH_RES_VIDEO_WIDTH
                    VIDEO_HEIGHT = HIGH_RES_VIDEO_HEIGHT
                    camera.resolution = (VIDEO_WIDTH, VIDEO_HEIGHT)
                    high_temp_triggered = False
                    
            # Record file name format: index_yyyy-mm-dd_HH-MM-SS.mp4
            time_now = datetime.now()
            rec_index = str(index)
            rec_time = time_now.strftime("%Y-%m-%d %H:%M:%S")
            rec_filename =  (rec_index 
                            +  '_' 
                            + time_now.strftime("%Y-%m-%d_%H-%M-%S") 
                            + RECORD_FORMAT_EXTENSION)
            rec_filepath = RECORDS_LOCATION + '/' + rec_filename
            
            video_format_text = "RPi DashCam {0}x{1} @ {2}fps".format(
                                    VIDEO_WIDTH,
                                    VIDEO_HEIGHT,
                                    VIDEO_FPS)
            
            CFG[CFG_CURR_INDEX_KEY] = index
            cfg_save()
            
            # Delete old record with same index number, 
            # Note: old record will have different time stamp on it. 
            existing_records = glob.glob(RECORDS_LOCATION 
                                + '/' 
                                + rec_index +  '_*')
            # There should be only one old record.
            for record in existing_records:
                os.remove(record)
                    
            mp4wfile = mp4writer.MP4Writer(filepath=rec_filepath,
                            fps=VIDEO_FPS)
            
            # Uncomment the below call to record directly to the 
            # underlying stdin object.
            #camera.start_recording(mp4wfile.get_file_object(),
            #                format='h264', quality=VIDEO_QUALITY)
            
            # Or use queue mechanism of mp4writer, this will
            # need more memory but no frame drops at higher resolutions.
            camera.start_recording(mp4wfile, format='h264',
                            quality=VIDEO_QUALITY)
            
            webinterface.WebInterfaceHandler.disk_space_used_percent = (
                    disk_used_space_percent)
            webinterface.WebInterfaceHandler.current_record_name = (
                    rec_filename)
            webinterface.WebInterfaceHandler.n_loops = n_loops
            
            webinterface.WebInterfaceHandler.is_recording_on = True
                            
            if high_temp_triggered:
                web_status_text = "Earlier temperature exceeded {0}&deg;C, " \
                                " video resolution reduced to {1}x{2}. " \
                                "High resolution will be restored after temperature drops " \
                                "below {3}&deg;C".format(
                                TEMPERATURE_THRESHOLD_HIGH,
                                VIDEO_WIDTH,
                                VIDEO_HEIGHT,
                                TEMPERATURE_THRESHOLD_NORMAL)
            else:
                web_status_text = "All OK"
            webinterface.WebInterfaceHandler.status_text = web_status_text
                    
            
            seconds = 0 
            got_stop_recording_cmd = False
            while seconds < DURATION_SEC:
                # update time
                rec_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                camera.annotate_text = (rec_index 
                                        + ' - ' 
                                        + rec_time 
                                        + ' - ' 
                                        + 'T ' + str(cpu_temp) + 'C - '
                                        + video_format_text
                                        + ' - '
                                        + fixed_annotation)
                
                # poll for any web command request
                if webinterface.WebInterfaceHandler.wcmd_rotate.requested():
                    current_rotation += 90
                    if current_rotation >= 360:
                            current_rotation = 0
                            
                    camera.rotation = current_rotation
                    webinterface.WebInterfaceHandler.wcmd_rotate.done()
                    
                    CFG[CFG_ROT_KEY] = current_rotation
                    cfg_save()
                        
                if webinterface.WebInterfaceHandler.wcmd_livesnap.requested():
                    camera.capture(LIVESNAP_LOCATION, use_video_port=True)
                    webinterface.WebInterfaceHandler.wcmd_livesnap.done()
                        
                if webinterface.WebInterfaceHandler.wcmd_stop_recording.requested():
                    got_stop_recording_cmd = True
                    break
                
                camera.wait_recording(1)
                seconds += 1
                    
            camera.stop_recording()
            
            mp4wfile.close()
            
            webinterface.WebInterfaceHandler.last_recorded_file = rec_filename
            index += 1
            
            if got_stop_recording_cmd:
                webinterface.WebInterfaceHandler.status_text = \
                    "Recording stopped by user at " \
                    "{0}. Camera closed.".format(rec_time)
                webinterface.WebInterfaceHandler.current_record_name = ''
                webinterface.WebInterfaceHandler.is_recording_on = False
                webinterface.WebInterfaceHandler.wcmd_stop_recording.done()
                break
               
        except Exception as e:
            logger.error(e)        
            logger.error('Recording Stopped')
            webinterface.WebInterfaceHandler.is_recording_on = False
            webinterface.WebInterfaceHandler.status_text = (
                "Internal error. Recording Stopped.<br>" 
                + str(e))
            break
finally:
    camera.close()
    logger.info('Camera closed. Waiting for web server to stop...')
    web_th.join()
