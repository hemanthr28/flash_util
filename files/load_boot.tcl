# How to use load.tcl
# source settings.sh of Vivado, SDK or PetaLinux in Bash
# xsct
# XSCT% source load.tcl
# XSCT% disconnect # when rerun needed or complete
set BOOTFILE "BOOT.BIN"

set IP "10.0.0.2"
set SPEED 15000000
set PORT "3121"
if {$argc > 0} {set BOOTFILE [lindex $argv 0]}
if {$argc > 1} {set IP [lindex $argv 1]}
if {$argc > 2} {set PORT [lindex $argv 2]}
if {$argc > 3} {set SPEED [lindex $argv 3]}


connect -url tcp:10.0.0.2:3121
# connect -host <IP> if using SmartLync or remote debug
#jtag frequency 12000000

jtag targets -set 1
jtag frequency $SPEED

target -set -filter {name =~ "Cortex-A53 #0"}

stop
dow -data $BOOTFILE 0x200000
con
after 2000
exec sleep 2

disconnect