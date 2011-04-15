#!/usr/bin/env python2.7

import plac
import pprint
import re
import sys
import socket

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi.builder import MibBuilder
from pysnmp.smi.view import MibViewController

# Depends on plac and pysnmp.

EXITCODE = { 'OK': 0, 'WARNING': 1, 'CRITICAL': 2, 'UNKNOWN': 3 }
STATUSES = { 0: 'OK', 1: 'WARNING', 2: 'CRITICAL', 3: 'UNKNOWN' }

SERVICE = "SNMP_INTERFACE"

METRIC_LIST = ['ifAdminStatus', 'ifDescr', 'ifIndex', 'ifInDiscards',
'ifInErrors', 'ifInNUcastPkts', 'ifInOctets', 'ifInUcastPkts',
'ifInUnknownProtos', 'ifLastChange', 'ifMtu', 'ifOperStatus', 'ifOutDiscards',
'ifOutErrors', 'ifOutNUcastPkts', 'ifOutOctets', 'ifOutQLen', 'ifOutUcastPkts',
'ifPhysAddress', 'ifSpecific', 'ifSpeed', 'ifType']

COUNTER_METRICS = ['ifInDiscards', 'ifInErrors', 'ifInNUcastPkts',
'ifInOctets', 'ifInUcastPkts', 'ifInUnknownProtos', 'ifOutDiscards',
'ifOutErrors', 'ifOutNUcastPkts', 'ifOutOctets', 'ifOutQLen', 'ifOutUcastPkts']

@plac.annotations(
        warning=("Warning value", 'option', 'w'),
        critical=("Critical value", 'option', 'c'),
        host=("Hostname", 'option', 'H'),
        port=("Port", 'option', 'P', int),
        debug=("Debug", 'flag', 'd'),
        community=("Community", 'option', 'C'),
        type=("Variable type", 'option', 't', str, ['be-higher-than',
            'be-lower-than', 'within-range', 'must-have-regex',
            'must-not-have-regex']),
        interface=("The interface to query", 'option', 'i'),
        metrics=("The metrics to retrieve", 'option', 'm', str, METRIC_LIST))
def main(warning, critical, debug, interface, type, community="public",
        host="localhost", port=161, *metrics):
    if debug:
        print "Arguments as parsed by plac:"
        print

        pprint.pprint(locals())

    modules = MibBuilder().loadModules('RFC1213-MIB')
    rfc1213 = MibViewController(modules)

    values = {}
    oids = []

    if not interface:
        print "CRITICAL: No interface specified!"
        sys.exit(EXITCODE['CRITICAL'])

    if not metrics:
        print "CRITICAL: No metrics specified!"
        sys.exit(EXITCODE['CRITICAL'])

    for metric in metrics:
        if metric not in METRIC_LIST:
            print "CRITICAL: %s not in metric list!" % metric
            sys.exit(EXITCODE['CRITICAL'])

        oid = rfc1213.getNodeNameByDesc(metric)[0]
        oids.append(oid + (int(interface),))

    try:
        cmd = cmdgen.CommandGenerator()

        errorIndication, errorStatus, \
        errorIndex, table = cmd.getCmd(
            cmdgen.CommunityData('nagios', community),
            cmdgen.UdpTransportTarget((host, port)),
            *oids)

        if errorIndication:
            print "CRITICAL: %s" % errorIndication
            sys.exit(EXITCODE['CRITICAL'])
        else:
            if errorStatus:
                print "CRITICAL: %s" % errorStatus.prettyPrint()
                sys.exit(EXITCODE['CRITICAL'])
            else:
                for row in table:
                    oid, value = row

                    p_oid, p_label, p_suffix = rfc1213.getNodeName(oid)

                    p_type = '.'.join(p_label[9:])
                    p_interface = '.'.join(str(i) for i in p_suffix)

                    # TODO: Add code path to print interface list
                    if debug:
                        if p_type == 'ifDescr':
                            print "%s.%s: %s" % (p_type, p_interface, value)

                    if p_type in metrics and p_interface == interface:
                        if debug:
                            print "%s.%s: %s" % (p_type, p_interface, value)

                        values[p_type] = value

    except socket.gaierror:
        print "CRITICAL: Unable to connect to the server."
        sys.exit(EXITCODE['CRITICAL'])

    status = 3

    if not warning and not critical:
        # Informational only, i.e. for pnp4nagios
        status = 0
    elif type in ['be-higher-than', 'be-lower-than']:
        warning = float(warning)
        critical = float(critical)

        statuses = []

        for key, value in values.items():
            value = float(value)

            statuses.append(test_in_range(value, warning, critical,
                type == 'be-lower-than'))

        status = max(statuses)
    elif type == 'within-range':
        # Ranges like 7.1-8.9. Overkill? Maybe.
        # TODO: Add support for Nagios-style ranges.
        re_range = re.compile("(\d+\.{0,1}\d*)[\- ]+(\d+\.{0,1}\d*)")

        try:
            warning_min, warning_max = map(float,
                    re_range.search(warning).groups())
            critical_min, critical_max = map(float,
                    re_range.search(critical).groups())
        except:
            print "%s CRITICAL: Error parsing arguments." % SERVICE

            sys.exit(EXITCODE['CRITICAL'])

        value = float(value)

        status = max(test_in_range(value, warning_min, critical_min, False),
                     test_in_range(value, warning_max, critical_max))
    elif type in ['must-have-regex', 'must-not-have-regex']:
        re_warning = re_critical = None

        try:
            if warning:
                re_warning = re.compile(warning)
            if critical:
                re_critical = re.compile(critical)
        except:
            print "%s CRITICAL: Your regular expression was invalid." % SERVICE
            sys.exit(2)

        status = 0

        if re_warning:
            if (re_warning.search(value) is not None) == \
                    (type == 'must-not-have-regex'):
                status = 1

        if re_critical:
            if (re_critical.search(value) is not None) == \
                    (type == 'must-not-have-regex'):
                status = 2

    if debug:
        pprint.pprint(values)

    print "%s %s: %s|%s" % (SERVICE, STATUSES[status], format_values(values),
            format_perfdata(metrics, values, warning, critical))

    sys.exit(status)

def format_values(values):
    return ', '.join(["%s: %s" % (k, v) for k, v in values.items()])

def format_perfdata(metrics, values, warning, critical):
    output = ""

    for metric in metrics:
        value = values[metric]

        if metric in COUNTER_METRICS:
            unit = "c"
        elif metric == "ifLastChange":
            unit = "s"
        else:
            unit = ""

        if type(value) == float:
            output += "%s=%0.2f%s" % (metric, value, unit)
        else:
            output += "%s=%s%s;" % (metric, value, unit)

        if isinstance(warning, float):
            output += "%0.2f;" % warning
        else:
            output += ";"

        if isinstance(critical, float):
            output += "%0.2f;" % critical
        else:
            output += ";"

        output += "; " # We don't worry about min/max at present

    return output

def test_in_range(v, w, c, higher=True):
    status = 0

    if (v > w) == higher:
        status = 1

    if (v > c) == higher:
        status = 2

    return status

if __name__ == "__main__":
    plac.call(main)
