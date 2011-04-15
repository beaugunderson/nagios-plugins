#!/usr/bin/env python2.7

import json
import os
import plac
import pprint
import sys
import subprocess

EXITCODE = { 'OK': 0, 'WARNING': 1, 'CRITICAL': 2, 'UNKNOWN': 3 }
STATUSES = { 0: 'OK', 1: 'WARNING', 2: 'CRITICAL', 3: 'UNKNOWN' }

SERVICE = "ESXI_ALARMS"

@plac.annotations(
        warning=("Warning value", 'option', 'w'),
        critical=("Critical value", 'option', 'c'),
        host=("Hostname", 'option', 'H'),
        username=("Username", 'option', 'u'),
        password=("Password", 'option', 'p'),
        debug=("Debug", 'flag', 'd'))
def main(warning, critical, debug, username, password, host="localhost"):
    if debug:
        print "Arguments as parsed by plac:"
        pprint.pprint(locals())

    status = EXITCODE['UNKNOWN']

    script = 'check_vsphere_alarms.pl'
    path = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(path, script)

    if debug:
        print script_path

    try:
        output = subprocess.check_output([script_path, '--server', host,
            '--username', username, '--password', password],
            stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, OSError) as e:
        print "CRITICAL: Error calling subprocess: %s" % e
        sys.exit(EXITCODE['CRITICAL'])
    except:
        print" CRITICAL: Unknown error."
        sys.exit(EXITCODE['CRITICAL'])

    if debug:
        print output

    output = output.replace(',]', ']')
    data = json.loads(output)

    state = [a['state'] for a in data]

    if debug:
        print data
        print state

    status = EXITCODE['OK']

    if 'yellow' in state:
        status = EXITCODE['WARNING']

    if 'red' in state:
        status = EXITCODE['CRITICAL']

    print "%s %s: %d alarms present|%s" % (SERVICE, STATUSES[status],
            len(data), format_values(data))

    sys.exit(status)

def format_values(values):
    if len(values):
        return "json(%s)" % json.dumps(values)
    else:
        return "No alarms"

if __name__ == "__main__":
    plac.call(main)
