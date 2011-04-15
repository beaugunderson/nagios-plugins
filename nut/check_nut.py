#!/usr/bin/env python2.7

import plac
import pprint
import PyNUT
import re
import sys

# Depends on having plac and PyNUT installed.

EXITCODE = { 'OK': 0, 'WARNING': 1, 'CRITICAL': 2, 'UNKNOWN': 3 }
STATUSES = { 0: 'OK', 1: 'WARNING', 2: 'CRITICAL', 3: 'UNKNOWN' }

SERVICE = "NUT"

@plac.annotations(
        warning=("Warning value", 'option', 'w'),
        critical=("Critical value", 'option', 'c'),
        host=("Hostname", 'option', 'H'),
        port=("Port", 'option', 'P'),
        ups=("UPS name", 'option', 'u'),
        debug=("Debug", 'flag', 'd'),
        login=("Login", 'option', 'l'),
        password=("Password", 'option', 'p'),
        type=("Variable type", 'option', 't', str, ['be-higher-than',
            'be-lower-than', 'within-range', 'must-have-regex',
            'must-not-have-regex']),
        variable="The variable to query")
def main(warning, critical, variable, debug, ups="ups1", login="upsmon",
        password="upsmon", host="localhost", port="3493", type="higher"):
    nut = PyNUT.PyNUTClient(host=host, login=login, password=password,
            debug=debug)

    variables = nut.GetUPSVars(ups)

    if debug:
        pprint.pprint(variables)

    if variable not in variables:
        print "%s CRITICAL: Error: Variable %s not found." \
                % (SERVICE, variable)
        sys.exit(2)

    status = 3

    value = variables[variable]

    if type in ['be-higher-than', 'be-lower-than']:
        warning = float(warning)
        critical = float(critical)

        value = float(value)

        status = test_in_range(value, warning, critical,
                type == 'be-lower-than')
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
            sys.exit(2)

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

    print "%s %s: %s: %s|%s" % (SERVICE, STATUSES[status], variable, value,
            format_perfdata(variable, value, warning, critical))

    sys.exit(EXITCODE[STATUSES[status]])

def format_perfdata(variable, value, warning, critical):
    output = "%s=%s;" % (variable, value)

    if isinstance(warning, float):
        output += "%f;" % warning
    else:
        output += ";"

    if isinstance(critical, float):
        output += "%f;" % critical
    else:
        output += ";"

    output += ";" # We don't worry about min/max at present

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
