#! /usr/bin/python2
from __future__ import print_function
from serial import Serial
from serial.serialutil import SerialException
from subprocess import call
from argparse import ArgumentParser
import subprocess
import sys
import os
import time
import glob

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_PORT = '/dev/ttyUSB0'
DEFAULT_SPEED = 115200
UBOOT_ERASE_SIZE = 0x08000000
UBOOT_BIN_ADDR_RAM = 0x00200000
LOAD_UBOOT_TCL_FILE = "files/load_uboot.tcl"
BOOTFILE = SCRIPT_PATH + '/BOOT.BIN'
PWD = os.getcwd()


def clean_exit(code):
    os.chdir(PWD)
    sys.exit(code)


def get_port_name(vendor, product, override):
    """Return the port name based on VID:PID

    Serial port names can change on the fly. Using this, you can
    make sure you are getting the correct serial port.

    Parameters
    ----------
    vendor : int
        Vendor ID.
    product : int
        Product ID.
    override : str
        Ignore the search and use the override.

    Returns
    -------
    str
        Port name.
    """
    if override is not None:
        return override
    
    # Loop through the list of USB serial ports.
    for device in glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'):
        base = os.path.basename(device)

        if os.path.exists('/sys/class/tty/%s/device' % (base,)):
            sys_dev_path = '/sys/class/tty/%s/device/driver/%s' % (base, base)

            if os.path.exists(sys_dev_path):
                sys_usb = os.path.dirname(os.path.dirname(os.path.realpath(sys_dev_path)))

                def get_info(sys_usb, filename):
                    with open(sys_usb + '/' + filename) as f:
                        data = f.read()
                        return int(data[:-1], 16)

                # Check if we have a match.
                if vendor == get_info(sys_usb, 'idVendor') and product == get_info(sys_usb, 'idProduct'):
                    return device
                    
    print('USB UART not found')
    sys.exit(1)


def get_into_uboot_prompt(port=DEFAULT_PORT):
    """Get into Uboot prompt.
    
    Attempt to get into Uboot prompt.
    
    Parameters
    ----------
    port : str
        The port name for the serial device to connect to.
    """
    try:
        ser = Serial(port, DEFAULT_SPEED, timeout=0.1)
    except SerialException as e:
        print(e)
        sys.exit(1)

    start_time = time.time()
    while time.time() < (start_time + 60.0):
        if ser.inWaiting():
            start_time = time.time()
            line = ser.readline().decode("utf-8")
            print(line[:-1])

            ser.write("\n".encode("utf-8"))
            if 'ZynqMP>' in line:
                return

    print('ERROR: Timed out (60).')
    clean_exit(1)


def run_uboot_command(command, port=DEFAULT_PORT, timeout=60.0):
    """Run Uboot command.
    
    Run a command on Uboot.
    
    Parameters
    ----------
    command : str
        Command to execute.
    port : str
        Name of the serial port to use.
    timeout : float
        Length of time before we time out and quit.
        
    Returns
    -------
    str
        Output from the serial interface.
    """
    ser = Serial(port, 115200, timeout=0.1)
    command=command + '\n'
    ser.write(command.encode("utf-8"))
    output = []

    start_time = time.time()
    while time.time() < (start_time + timeout):
        if ser.inWaiting():
            start_time = time.time()
            line = ser.readline().decode("utf-8").replace('\n', '')
            output.append(line)
            print('>>>: ' + line)
            sys.stdout.flush()

            # Check to see if latest line is the UBoot command prompt.
            if 'ZynqMP>' in line:
                return '\n'.join(output)

    print('ERROR: run_uboot_command() Timed out ({}).'.format(timeout))
    clean_exit(1)


if __name__ == '__main__':

    # Get the 250-SoC into its UBoot prompt.
    cwd = os.getcwd()
    os.chdir(SCRIPT_PATH)
    parser = ArgumentParser()
    parser.add_argument("-b", "--bootfile", dest="filename", help="Boot file to program to flash", metavar="FILE")
    parser.add_argument("-p", "--port", dest="portname", help="TTY port name", metavar="FILE")
    parser.add_argument("-e", "--eraseonly", action="store_true", help="Erase flash and exit")
    parser.add_argument("-j", "--jtag_ip", dest="jtag_ip", help="IP address of the smartlynq cable", metavar="FILE")
    parser.add_argument("-k", "--jtag_port", dest="jtag_port", help="JTAG port number", metavar="FILE")
    parser.add_argument("-s", "--jtag_speed", dest="jtag_speed", help="JTAG clock speed", metavar="FILE")

    args = parser.parse_args()
    
    if args.filename:
        filename = os.path.abspath(args.filename)
    else:
        filename = BOOTFILE

    if args.portname:
        portname_override = args.portname
    else:
        portname_override = None
        
    if args.jtag_ip:
        jtag_ip = args.jtag_ip
    else:
        jtag_ip = "127.0.0.1"
        
    if args.jtag_port:
        jtag_port = args.jtag_port
    else:
        jtag_port = "3121"

    if args.jtag_speed:
        jtag_speed = args.jtag_speed
    else:
        jtag_speed = "15000000"

    os.chdir("files")
    call(["xsct", "load_uboot.tcl",jtag_ip,jtag_port,jtag_speed])
    get_into_uboot_prompt(port=get_port_name(0x0403, 0x6015, portname_override))
 
    if not args.eraseonly:
        print("About to download image to u-boot.  This might take a while depending on size of image and JTAG pod used.")
        call(["xsct", "load_boot.tcl",filename,jtag_ip,jtag_port,jtag_speed])
        size = os.path.getsize(filename)

    run_uboot_command("true", port=get_port_name(0x0403, 0x6015, portname_override))
    run_uboot_command("sf probe", port=get_port_name(0x0403, 0x6015, portname_override))
    run_uboot_command('sf erase 0x0 0x{0:x}'.format(UBOOT_ERASE_SIZE), port=get_port_name(0x0403, 0x6015, portname_override),timeout=300)
    if not args.eraseonly:
        run_uboot_command('sf write 0x{0:x} 0x0 0x{1:x}'.format(UBOOT_BIN_ADDR_RAM, size), port=get_port_name(0x0403, 0x6015, portname_override), timeout=600)
    run_uboot_command("mw.l 0xff5e0200 0x00002100 1",port=get_port_name(0x0403, 0x6015, portname_override))
    run_uboot_command("true", port=get_port_name(0x0403, 0x6015, portname_override))
    os.chdir(cwd)

    if args.eraseonly:
        print('\nFinished Erasing Flash.')
    else:
        print('\nFinished Programming ARM.')
    clean_exit(0)
