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

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from socketserver import ThreadingMixIn
import cgi
import os
from datetime import timedelta
from datetime import datetime
import traceback
import urllib.parse as url_parse
import threading
import subprocess
import time
import glob
import pathlib
import shutil
import logging

import webcommand
import util

logger = logging.getLogger(__name__)

_SERVER_ADDRESS = ('', 8080)

_MINUTE_SEC = 60
_HOUR_SEC = 60 * _MINUTE_SEC

# -------------------------------------
# main module will update these variables before starting 
# web server.
RECORDS_LOCATION = "."
RECORD_FORMAT_EXTENSION = ".h264"
HOME = os.getcwd()
# ------------------------------------

LIVESNAP_NAME = "live_snap.jpg"
SOFTWARE_VERSION = "1.1.0"

_HTTP_STATUS_CODE_BAD_REQUEST = 400
_HTTP_STATUS_CODE_REQUEST_TIMEOUT = 408
_HTTP_STATUS_CODE_NOT_FOUND = 404
_HTTP_STATUS_CODE_INTERNAL_SERVER_ERROR = 500

_HTTP_STATUS_CODE_OK = 200
_HTTP_STATUS_CODE_REDIRECT = 302

class WebInterfaceHandler(BaseHTTPRequestHandler):
    # Each request handler runs in its own thread.
    
    # Shared static variables with no synchronizers.
    # current status of the program
    status_text = 'Not yet set'
    # Calculate uptime with it.
    program_start_time = None
    # User can playback last recorded video on home page, post powerup
    # wait until one recording is over.
    last_recorded_file = ''
    
    # Shared static variables with synchronizers.
    wcmd_livesnap = webcommand.WebCommandSync()
    wcmd_rotate = webcommand.WebCommandSync()
    wcmd_stop_recording = webcommand.WebCommandSync()
        
    def do_GET(self):
        # Serve URLs, POST method not used in html files.
        # url are at root level.
        
        # Rather than a long list of if-else chain dictionary indexing
        # from path to function might be better ??
        try:
            if self.path == '/':
                self.serve_index()
            elif self.path == '/reboot':
                self.serve_reboot()
            elif self.path == '/poweroff':
                self.serve_shutdown()
            elif self.path == '/view-records':
                self.serve_view_records()
            elif '/get-record' in self.path:
                # This url will have paramters: ?f=<name>
                # convert them into key value pairs.
                kv = self.parse_get_params()
                if 'f' in kv:
                    self.serve_record(kv['f'][0], True)        
                else:
                    self.send_error(_HTTP_STATUS_CODE_BAD_REQUEST)
            elif '/play-record' in self.path:
                # This url will have paramters: ?f=<name>
                # convert them into key value pairs.
                kv = self.parse_get_params()
                if 'f' in kv:
                    self.serve_record(kv['f'][0], False)        
                else:
                    self.send_error(_HTTP_STATUS_CODE_BAD_REQUEST)
            elif self.path == '/rotate':
                WebInterfaceHandler.wcmd_rotate.start()
                if WebInterfaceHandler.wcmd_rotate.wait(5):
                    self.redirect_to_home()
                else:
                    self.send_error(_HTTP_STATUS_CODE_REQUEST_TIMEOUT)
            elif self.path == '/livesnap':
                self.serve_snap()
            elif self.path == '/stop':
                # For now only reboot can start camera/recording
                WebInterfaceHandler.wcmd_stop_recording.start()
                if WebInterfaceHandler.wcmd_stop_recording.wait(5):
                    self.redirect_to_home()
                else:
                    self.send_error(_HTTP_STATUS_CODE_REQUEST_TIMEOUT)
            elif self.path.endswith(RECORD_FORMAT_EXTENSION):
                self.serve_record(self.path.lstrip("/"), False)
            else:
                msg = "Requested URI: '" + self.path + "' not found."
                self.send_error(_HTTP_STATUS_CODE_NOT_FOUND, 
                            explain=msg)
            return
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
                        
    def parse_get_params(self):
        # Convert url query string into key value pairs.
        query = url_parse.urlsplit(self.path).query
        params = url_parse.parse_qs(query)
        return dict(params)
            
    def serve_index(self):
        self.home_page()
    
    def serve_reboot(self):
        self.redirect_to_home()
        os.system("sudo reboot")
    
    def serve_shutdown(self):
        self.redirect_to_home()
        os.system("sudo poweroff")
                    
    def redirect_to_home(self):
        self.send_response(_HTTP_STATUS_CODE_REDIRECT) 
        self.send_header('Location', '/')
        self.end_headers()
        self.flush_headers()
            
    def serve_record(self, recname, download_play):
        # Either send the record file as attachment for download 
        # (download_play == true) or as
        # content (download_play == false)
        filepath = RECORDS_LOCATION + '/' + recname
        
        if os.path.exists(filepath) == False:
            self.send_error(_HTTP_STATUS_CODE_NOT_FOUND)
            return
        
        fileobj = None
        
        # Handle file opening error early, if file's recording is in
        # progress then reading it will cause lock error.
        try:
            fileobj = open(filepath, 'rb')
        except Exception as e:
            self.send_error(_HTTP_STATUS_CODE_INTERNAL_SERVER_ERROR,
                        explain=str(e))
            return
                
        self.send_response(_HTTP_STATUS_CODE_OK)
        
        file_len = os.path.getsize(filepath)
        if download_play: #download as file
            self.send_header('Content-type','application/octet-stream')
            self.send_header('Content-Disposition', 
                            "attachment;filename=" + recname)
        else: #play
            self.send_header('Content-type','video/mp4')
                        
        self.send_header('Content-Length', str(file_len))
        self.end_headers()
        
        try:
            shutil.copyfileobj(fileobj, self.wfile)
            fileobj.close()
        except ConnectionResetError as e:
            logger.warning(e)
        except BrokenPipeError as e:
            logger.warning(e)
        
    def serve_view_records(self):
        # loads view-records.html page in memory and replace its
        # keywords with corresponding contents.
        self.send_response(_HTTP_STATUS_CODE_OK)
        
        self.send_header('Content-type','text/html')
        filepath = HOME + '/html/view-records.html'  
        
        page = ''
        with open(filepath, 'r') as f:
            page = f.read()
        
        rec_table_rows = ''
        serial_no = 0;
        rec_files = glob.glob(RECORDS_LOCATION + '/*' 
                        + RECORD_FORMAT_EXTENSION)
        rec_files.sort(key=os.path.getmtime, reverse=True)
        
        for record in rec_files:
            rec_filename = pathlib.Path(record).name
            serial_no += 1
            rec_table_rows += """
                     <tr>
                            <td>{0}</td>
                            <td><a href="get-record?f={1}">{2}</a></td>
                            <td><button title="Play Record" onclick='play_rec("{3}");'>&#9658;</button></td>
                     </tr>
                    """.format(serial_no, rec_filename, 
                                rec_filename, rec_filename)
        
        page = page.replace('_REC_TABLE_ROWS', rec_table_rows)
        
        self.send_header('Content-Length', str(len(page)))
        self.end_headers()
        self.wfile.write(bytes(page, "utf8"))
                
    def home_page(self):
        # loads home.html page in memory and replace its
        # keywords with corresponding contents.
        self.send_response(_HTTP_STATUS_CODE_OK)
        self.send_header('Content-type','text/html')
        filepath = HOME + '/html/home.html'  
        
        page = ''
        with open(filepath, 'r') as f:
                page = f.read()
        page = page.replace('_VERSION', str(SOFTWARE_VERSION))
        
        page = page.replace('_STATUS', WebInterfaceHandler.status_text)
        
        # Update SoC temperature
        cpu_temp = util.get_cpu_temperature()
        page = page.replace('_STEMP', str(cpu_temp) + "&deg;C")
        
        # Caluclate program uptime not system.
        duration = datetime.now() - WebInterfaceHandler.program_start_time
        total_secs = int(duration.seconds)
        uptime = ''
        if total_secs >= _HOUR_SEC:
            hours = int(total_secs / _HOUR_SEC)
            total_secs = total_secs % _HOUR_SEC
            uptime += "{0} hours ".format(hours)
        if total_secs > _MINUTE_SEC:
            mins = int(total_secs / _MINUTE_SEC)
            total_secs = total_secs % _MINUTE_SEC
            uptime += "{0} mins ".format(mins)
        uptime += "{0} seconds ".format(total_secs)
        page = page.replace('_UPTIME', uptime)
        
        page = page.replace('_WEB_COMMANDS', 
                '<a href="view-records">View/Download Records</a>&nbsp;&nbsp;&nbsp;&nbsp;' 
                + '<a href="/rotate">Rotate 90&deg; &#x21bb;</a>&nbsp;&nbsp;&nbsp;&nbsp;' 
                + '<a href="/stop">Stop Recording</a>&nbsp;&nbsp;&nbsp;&nbsp;' 
                + '<a href="/reboot">Reboot</a>&nbsp;&nbsp;&nbsp;&nbsp;' 
                + '<a href="/poweroff">Power Off</a>')
        
        page = page.replace('_LRV_FILE', WebInterfaceHandler.last_recorded_file)
        
        self.send_header('Content-Length', str(len(page)))
        self.end_headers()
        
        self.wfile.write(bytes(page, "utf8"))
    
    def serve_snap(self):
        # Get current video snapshot, a low cost way 
        # to check whether camera is running ok.
        WebInterfaceHandler.wcmd_livesnap.start()
        if WebInterfaceHandler.wcmd_livesnap.wait(5) == False:
            self.send_error(_HTTP_STATUS_CODE_INTERNAL_SERVER_ERROR)
            return
                
        self.send_response(_HTTP_STATUS_CODE_OK)
        self.send_header('Content-type','image/jpeg')
                
        try:
            filepath = RECORDS_LOCATION + "/" + LIVESNAP_NAME
            file_len = os.stat(filepath).st_size
            self.send_header('Content-Length', str(file_len))
            self.end_headers()
            with open(filepath, 'rb') as f:
                try:
                    shutil.copyfileobj(f, self.wfile)
                except ConnectionResetError as e:
                    logger.warning(e)
                except BrokenPipeError as e:
                    logger.warning(e)    
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)


class ThreadingWebServer(ThreadingMixIn, HTTPServer):
    # Make each request handler run in its own thread.
    # Improves browser performance and user experience.
    pass
            
def _start_webserver():
    server = ThreadingWebServer(_SERVER_ADDRESS, WebInterfaceHandler)
    server.serve_forever()

def start():
    # called from main module
    th = threading.Thread(target=_start_webserver)
    th.daemon = True
    th.start()
    return th
               
if __name__ == "__main__":
    # For testing in standalone mode.
    try:
        WebInterfaceHandler.program_start_time = datetime.now()
        _start_webserver()
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(e)
