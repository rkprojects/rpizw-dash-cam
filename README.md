# Dash Camera with Raspberry Pi Zero W

The small form factor of [Raspberry Pi Zero W](https://www.raspberrypi.org/products/raspberry-pi-zero-w/) along with its official cases makes it ideal for many camera based applications, so I thought why not make a dash camera with it for fun.

Project home page is at <https://ravikiranb.com/projects/rpizw-dash-cam/>

## Hardware Requirements

* Raspberry Pi Zero W board along with its official cases, especially the camera case.
* Raspberry Pi Camera Module V1 or V2 version.  
* **High Endurance** micro SD card - This is critical if you intend to record continuously or recording 
  at FULL HD format.
* WiFi access point (AP) source for syncing time from internet as there is no RTC/battery on RPi Zero W.  
    Instructions on how to configure WiFi from command line is [here](https://www.raspberrypi.org/documentation/configuration/wireless/wireless-cli.md).
  
## Software Requirements

* OS - Raspbian GNU/Linux 9 (stretch) Lite or with desktop.  
    You can check the version already installed by reading os-release file.  
    
    $ cat /etc/os-release
    
    If you intend to go with desktop version of Raspbian then please change boot preference to command
    line in [raspi-config](https://www.raspberrypi.org/documentation/configuration/raspi-config.md)          tool to reduce memory consumption and startup time.  
    Instructions on how to install OS image is [here](https://www.raspberrypi.org/documentation/installation/installing-images/README.md).  

* Enable remote access with SSH, this is optional but useful as you won't need another keyboard and display to connect to RPi.  
    Instructions on how to enable SSH is [here](https://www.raspberrypi.org/documentation/remote-access/ssh/).

* Python version 3.5 or more, if not already installed:  

    $ sudo apt install python3

* Python3 picamera module, if not already installed:  

    $ sudo apt install python3-picamera  
    
    Instructions on how to enable the camera is [here](https://www.raspberrypi.org/documentation/configuration/camera.md).

* FFmpeg, if not already installed:  

    $ sudo apt install ffmpeg

* Git, if not already installed:  

    $ sudo apt install git

* Controlling the Dash Camera with smart phone on bluetooth (BLE) interface will require:  
    * BlueZ stack version [5.50](http://www.bluez.org/release-of-bluez-5-50/):  
        You might have to manually compile and install it if its not available with **apt**  
        Please refer to its Readme and Install file in source code.
    * Modify BlueZ daemon configuration file */etc/dbus-1/system.d/bluetooth.conf*:  
        Add the following **bluetooth** group policy in the configuration file to avoid 
        running the program as sudo/root, and add your user account to group **bluetooth**:  
        ```
        <policy group="bluetooth">
            <allow own="org.bluez"/>
            <allow send_destination="org.bluez"/>
            <allow send_interface="org.bluez.Agent1"/>
            <allow send_interface="org.bluez.Profile1"/>
            <allow send_interface="org.bluez.GattService1"/>
            <allow send_interface="org.bluez.GattCharacteristic1"/>
            <allow send_interface="org.bluez.GattDescriptor1"/>
            <allow send_interface="org.bluez.LEAdvertisement1"/>
            <allow send_interface="org.freedesktop.DBus.ObjectManager"/>
            <allow send_interface="org.freedesktop.DBus.Properties"/>
      </policy>
      ```
      
    * Python dbus module to access bluez D-Bus APIs:  
        $ sudo apt install python3-dbus python3-gi

## Install

Ensure that RPi is connected to WiFi and Internet.

### Get Source Code

$ git clone https://github.com/rkprojects/rpizw-dash-cam.git  
$ cd rpizw-dash-cam  
$ ./install.sh  
$ ./run.sh

### Access Web Interface

Open web browser on your computer and access http://raspberrypi.local:8080/

### Access Bluetooth Interface on Smartphone

The Dash Camera application starts a GATT server in peripheral mode and starts advertisement by default for 180 seconds. For now there is no security/authentication anyone can connect and control.

On Android install Nordic semiconductor's [nRF Connect for Mobile](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp) app, you can use any app that can scan and explore BLE GATT services.

Dash Camera will appear as **RPi DashCam** device after scanning. Connect to it and explore its custom
service, read out all the characteristics and/or enable notifications.  
Each characteristic has a *Characteristic User Description Descriptor* to describe its purpose.

## License

Copyright (C) 2019 Ravikiran Bukkasagara, <contact@ravikiranb.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Please refer to the file **COPYING** for complete GNU General Public License text.
