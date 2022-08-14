# How to use load.tcl
# source settings.sh of Vivado, SDK or PetaLinux in Bash
# xsct
# XSCT% source load.tcl
# XSCT% disconnect # when rerun needed or complete
set IP "10.0.0.2"
set SPEED 15000000
set PORT "3121"
if {$argc > 0} {set IP [lindex $argv 0]}
if {$argc > 1} {set PORT [lindex $argv 1]}
if {$argc > 2} {set SPEED [lindex $argv 2]}

connect -url tcp:10.0.0.2:3121
# connect -host <IP> if using SmartLync or remote debug

#jtag targets -set -filter {name =~ "Platform Cable USB*"}
#jtag frequency 12000000

jtag targets -set 1
jtag frequency $SPEED

after 2000
target -set -filter {name =~ "Cortex-A53 #0"}
rst
after 2000

# show PMU MicroBlaze on JTAG chain 
targets -set -nocase -filter {name =~ "*PSU*"}
mwr 0xFFCA0038 0x1FF

# Download PMUFW to PMU
target -set -filter {name =~ "MicroBlaze PMU"}
dow pmufw.elf
after 2000
con
targets -set -nocase -filter {name =~ "*PSU*"}
mwr 0xFFFF0000 0x14000000
mwr 0xFD1A0104 0x380E

# Run FSBL
target -set -filter {name =~ "Cortex-A53 #0"}
rst -processor
dow zynq_fsbl_jtag.elf
after 2000
con
after 2000
exec sleep 2
stop

# Run U-boot
targets -set -nocase -filter {name =~ "*A53*#0"}
dow u-boot.elf
dow bl31.elf
con

#disconnect
#exec sleep 10
#stop
#after 2000
#dow -data BOOT.BIN 0x200000
#con
#fpga bist_ph1_top.bit

disconnect

