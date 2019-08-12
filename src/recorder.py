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



import time
import picamera
from datetime import datetime
import json
import os
import subprocess
import glob
import sys
import logging
import util
import threading
import queue
import traceback

import mp4writer
from command import Command
import config

logger = logging.getLogger(__name__)


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
_cfg = { 
    CFG_ROT_KEY: 0,
    CFG_CURR_INDEX_KEY: 0,
    CFG_MAX_FILES_KEY:0,
    CFG_N_LOOPS_KEY: 0
}

KB = 1024
MB = KB * KB

# Read only variables for other modules.
# No synchronization. Merely to show on user interface.
current_record_name = ""
last_recorded_name = "Please wait for one recording to be over"
n_loops = 0
recording_on = False
recording_status_text = ""
# -------------------------------------


# Internal global variables
_VIDEO_WIDTH = config.HIGH_RES_VIDEO_WIDTH
_VIDEO_HEIGHT = config.HIGH_RES_VIDEO_HEIGHT

_th_recorder = None
_stop = True


_cpu_temp_subscribers = []
_status_subscribers = []
_subscribers_lock = threading.Lock()
_cmd_q = queue.Queue()

# ---------------------------------------

def _update_subs_on_status(status):
    with _subscribers_lock:
        for s in _status_subscribers:
            s(status)
        
def _update_subs_on_cpu_temp(temp):
    with _subscribers_lock:
        for s in _cpu_temp_subscribers:
            s(temp)
            
def subscribe_for_cpu_temp(cb):
    with _subscribers_lock:
        _cpu_temp_subscribers.append(cb)

def subscribe_for_status(cb):
    with _subscribers_lock:
        _status_subscribers.append(cb)


def _cfg_save():
    global _cfg
    with open(config.CFG_FILE, 'w') as f:
        json.dump(_cfg, f)

        
def get_disk_space_info():
    params = None
    try:
        # get disk space info of the "filesystem" where recordings 
        # are stored, in case multiple storage options are available in
        # future.
        op = subprocess.check_output(['df',
                        config.RECORDS_LOCATION]).decode('utf-8').split('\n')
        params = op[1].split()                
        params[4] = int(params[4].strip('%')) # Percent used
        # params[1] = int(params[1]) * KB # Disk Size - bytes
        # params[2] = int(params[2]) * KB # Used size - bytes
        # params[3] = int(params[3]) * KB # Available size - bytes
        # return (params[1], params[2], params[3], params[4])
        return params[4]
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return None



def init():
    global _cfg
    
    # Load existing configuration file or start fresh.
    if os.path.exists(config.CFG_FILE):
        with open(config.CFG_FILE, 'r') as f:
            _cfg = json.load(f)

def start():
    global _th_recorder
    global _stop
    
    if _stop:
        _th_recorder = threading.Thread(target=_loop_recoder)
        _stop = False
        _th_recorder.start()
    
def stop():
    global _th_recorder
    global _stop
    if _th_recorder:
        _stop = True
        _th_recorder.join()
        
def queue_commands(request):
    _cmd_q.put(request)

def _build_timestamp(forfile=True):
    if forfile:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S") 
    else:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S") 


def _loop_recoder():
    global _cfg
    global _stop
    global _VIDEO_WIDTH
    global _VIDEO_HEIGHT
    global n_loops
    global current_record_name
    global last_recorded_name
    global recording_on
    global recording_status_text
    
    recording_status_text = "Initializing Pi Camera to {0}x{1} @ {2} fps".format(
                _VIDEO_WIDTH, _VIDEO_HEIGHT, config.VIDEO_FPS)
    logger.info(recording_status_text)
    _update_subs_on_status(recording_status_text)
    
    # Initialize camera
    camera = picamera.PiCamera()
    camera.resolution = (_VIDEO_WIDTH, _VIDEO_HEIGHT)
    camera.framerate_range = (1, config.VIDEO_FPS)
    camera.framerate = config.VIDEO_FPS
    camera.annotate_background = True
    fixed_annotation =  "RavikiranB.com"
    camera.annotate_text_size = config.ANNOTATE_TEXT_SIZE
    current_rotation = _cfg[CFG_ROT_KEY]
    camera.rotation = current_rotation
    
    location_text = None
    
    try:
        index = _cfg[CFG_CURR_INDEX_KEY] + 1
        n_loops = _cfg[CFG_N_LOOPS_KEY]
        
        recording_status_text = "Starting Recording."
        _update_subs_on_status(recording_status_text)
        
        #webinterface.WebInterfaceHandler.program_start_time = datetime.now()
        high_temp_triggered = False
        
        recording_on = True
        
        while not _stop:
            try:        
                disk_used_space_percent = get_disk_space_info()
                    
                if _cfg[CFG_MAX_FILES_KEY] == 0:
                    if (disk_used_space_percent >= 
                            config.MAX_USED_DISK_SPACE_PERCENT):
                        # From now on recording index will loop 
                        # back to zero when index 
                        # reaches _cfg[CFG_MAX_FILES_KEY]
                        _cfg[CFG_MAX_FILES_KEY] = index
                        index = 0
                        n_loops += 1
                        _cfg[CFG_N_LOOPS_KEY] = n_loops
                elif index >= _cfg[CFG_MAX_FILES_KEY]:
                    index = 0
                    n_loops += 1
                    _cfg[CFG_N_LOOPS_KEY] = n_loops
                        
                # Update SoC temperature in video annotation, to keep 
                # track of resolution drop vs temp.
                cpu_temp = util.get_cpu_temperature()
                if cpu_temp >= config.TEMPERATURE_THRESHOLD_HIGH:
                    if not high_temp_triggered:
                        logger.warning("CPU temperature %s C exceeded threshold %s C",
                                        cpu_temp, config.TEMPERATURE_THRESHOLD_HIGH)
                        logger.warning("Reducing video resolution")
                        _VIDEO_WIDTH = config.LOW_RES_VIDEO_WIDTH
                        _VIDEO_HEIGHT = config.LOW_RES_VIDEO_HEIGHT
                        camera.resolution = (_VIDEO_WIDTH, _VIDEO_HEIGHT)
                        high_temp_triggered = True
                elif cpu_temp <= config.TEMPERATURE_THRESHOLD_NORMAL:
                    if high_temp_triggered:
                        logger.warning("Restoring high video resolution")
                        _VIDEO_WIDTH = config.HIGH_RES_VIDEO_WIDTH
                        _VIDEO_HEIGHT = config.HIGH_RES_VIDEO_HEIGHT
                        camera.resolution = (_VIDEO_WIDTH, _VIDEO_HEIGHT)
                        high_temp_triggered = False
                        
                _update_subs_on_cpu_temp(cpu_temp)
                        
                # Record file name format: index_yyyy-mm-dd_HH-MM-SS.mp4
                rec_index = str(index)
                rec_time = _build_timestamp(forfile=False)
                rec_filename =  (rec_index 
                                +  '_' 
                                + _build_timestamp()
                                + config.RECORD_FORMAT_EXTENSION)
                rec_filepath = config.RECORDS_LOCATION + '/' + rec_filename
                
                video_format_text = "RPi DashCam {0}x{1} @ {2}fps".format(
                                        _VIDEO_WIDTH,
                                        _VIDEO_HEIGHT,
                                        config.VIDEO_FPS)
                
                _cfg[CFG_CURR_INDEX_KEY] = index
                _cfg_save()
                
                # Delete old record with same index number, 
                # Note: old record will have different time stamp on it. 
                existing_records = glob.glob(config.RECORDS_LOCATION 
                                    + '/' 
                                    + rec_index +  '_*')
                # There should be only one old record.
                for record in existing_records:
                    os.remove(record)
                        
                mp4wfile = mp4writer.MP4Writer(filepath=rec_filepath,
                                fps=config.VIDEO_FPS)
                
                # Uncomment the below call to record directly to the 
                # underlying stdin object.
                #camera.start_recording(mp4wfile.get_file_object(),
                #                format='h264', quality=config.VIDEO_QUALITY)
                
                # Or use queue mechanism of mp4writer, this will
                # need more memory but no frame drops at higher resolutions.
                camera.start_recording(mp4wfile, format='h264',
                                quality=config.VIDEO_QUALITY)
                
                current_record_name = rec_filename
                                
                if high_temp_triggered:
                    recording_status_text = "Temperature exceeded {0}&deg;C, " \
                                    " video resolution reduced to {1}x{2}. " \
                                    "High resolution will be restored after temperature drops " \
                                    "below {3}&deg;C".format(
                                    config.TEMPERATURE_THRESHOLD_HIGH,
                                    _VIDEO_WIDTH,
                                    _VIDEO_HEIGHT,
                                    config.TEMPERATURE_THRESHOLD_NORMAL)
                else:
                    recording_status_text = "All OK"
                    
                _update_subs_on_status(recording_status_text)
                
                seconds = 0 
                while (not _stop) and (seconds < config.DURATION_SEC):
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
                    
                    if location_text:
                        camera.annotate_text += '\n' + location_text
                    
                    # poll for any recorder related commands
                    try:
                        request = _cmd_q.get(block=False)
                        if request.cmd == Command.CMD_ROTATE:
                            current_rotation += 90
                            if current_rotation >= 360:
                                current_rotation = 0
                            camera.rotation = current_rotation
                            _cfg[CFG_ROT_KEY] = current_rotation
                            _cfg_save()
                            request.done()
                        elif request.cmd == Command.CMD_TAKE_LIVE_SNAPSHOT:
                            camera.capture(config.LIVESNAP_FILE, use_video_port=True)
                            request.done()
                        elif request.cmd == Command.CMD_SET_LOCATION_SPEED:
                            location_text = str(request.data)
                            request.done()
                    except queue.Empty:
                        pass
                    
                    camera.wait_recording(1)
                    seconds += 1
                    
                camera.stop_recording()
                
                mp4wfile.close()
                
                last_recorded_name = rec_filename
                
                index += 1
                
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(e)        
                logger.error('Recording Stopped')
                recording_status_text = "Internal error. Recording Stopped.<br>" + str(e)
                _update_subs_on_status(recording_status_text)
                break
    finally:
        recording_on = False
        camera.close()
        recording_status_text = "Recording stopped by user at " \
                        "{0}. Camera closed.".format(
                                _build_timestamp(forfile=False))
                                
        _update_subs_on_status(recording_status_text)

        
        
