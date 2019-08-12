#!/bin/bash

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

#
# Running this script will modify /etc/rc.local (take backup!) 
# to enable auto start on powerup. 
# To just try the application without installing run following commands
# in the checked out directory.
# 
# > mkdir records
# > cd src
# > python3 main.py ../records
#
# Enjoy...
#

# Do not run this script as root
if [ $EUID -eq 0 ]; then
    echo ""
    echo "Error: Do not run this script as root/sudo."
    echo ""
    exit -1
fi

# user must belong sudo group.
groups | grep -q sudo
if [ $? -ne 0 ]; then
    msg="\nCurrent user must be in sudo group for reboot, poweroff\n"
    msg+="to work from web browser. sudo is also required for\n"
    msg+="installing auto start entry in /etc/rc.local"
    echo -e $msg
    exit -1
fi

# build absolute paths
cwd=`pwd`
src_dir=$cwd/src

# Change record location if required, it must be absolute path.
records_dir=$cwd/records

if [ ! -d $records_dir ]; then
    mkdir $records_dir
    if [ $? -ne 0 ]; then
        exit -1
    fi
fi

run_script="run.sh"
install_marker="# _DCAM_APP_"
install_line="$cwd/$run_script"
rclocal="/etc/rc.local"

if [ ! -f $rclocal ]; then
    echo "Error: File $rclocal not found!"
    exit -1
fi

# Check if already installed
grep -q "$install_marker" $rclocal
if [ $? -eq 0 ]; then
    echo "Already installed. Replacing startup command in $rclocal"
    cmd="/^${install_marker}/{n;s@.*@${install_line}@;}"
    # echo $cmd
    sudo sed -i.bak "$cmd" ${rclocal}
else
    cmd="s@\(^exit 0\$\)@${install_marker}\n${install_line}\n\n&@"
    # echo $cmd
    sudo sed -i.bak "$cmd" ${rclocal}
fi

if [ $? -ne 0 ]; then
        exit -1
fi

echo "#!/bin/bash" > $run_script
echo "" >> $run_script
echo "# Auto generated." >> $run_script
echo "" >> $run_script
echo "cd $src_dir" >> $run_script
echo "sudo -H -u $USER python3 main.py -r \"$records_dir\" &" >> $run_script
chmod +x $run_script

if [ $? -ne 0 ]; then
        exit -1
fi

echo ""
echo "Installation done."
echo "Execute run.sh or reboot to auto start."
echo ""
