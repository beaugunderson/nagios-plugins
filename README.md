nagios-plugins
==============

Note: In all of the examples below I've omitted the host, username, and password for brevity.

nut
---

Alarms for Network UPS Tools.

Dependencies:

+ plac
+ PyNUT

Examples:

    $ ./check_nut.py --ups ups1 --type within-range --warning 112-128 --critical 110-130 input.voltage
    $ ./check_nut.py --ups ups1 --type be-higher-than --warning 95 --critical 90 battery.charge
    $ ./check_nut.py --ups ups1 --type be-lower-than --warning 40 --critical 45 battery.temperature
    $ ./check_nut.py --ups ups1 --type be-lower-than --warning 80 --critical 85 ups.load
    $ ./check_nut.py --ups ups1 --type must-have-regex --warning OL --critical OL ups.status
    $ ./check_nut.py --ups ups1 --type must-not-have-regex --warning RB --critical ALARM ups.status

snmp-traffic
------------

Alarms and statistical information for switch interface traffic.

Dependencies:

+ plac
+ pysnmp

Examples:

    $ ./check_snmp_traffic.py --interface 1 ifInOctets ifOutOctets

vsphere-alarms
--------------

This script is written in both Python and Perl. VMware distributes Perl API bindings so I've written a thin wrapper in Perl that returns JSON data which is parsed by the Python script.

Dependencies:

+ plac
+ VMware Perl modules

Examples:

    $ ./check_vsphere_alarms.py
