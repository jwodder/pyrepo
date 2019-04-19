import re
import subprocess
import sys
import time
from   in_place import InPlace
from   intspan  import intspan

def runcmd(*args, **kwargs):
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        sys.exit(r.returncode)

def readcmd(*args, **kwargs):
    try:
        return subprocess.check_output(args, universal_newlines=True, **kwargs)\
                         .strip()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

def ensure_license_years(filepath, years: 'list[int]'):
    with InPlace(filepath, mode='t', encoding='utf-8') as fp:
        for line in fp:
            m = re.match(r'^Copyright \(c\) (\d[-,\d\s]+\d) \w+', line)
            if m:
                line = line[:m.start(1)] + update_years2str(m.group(1), years) \
                     + line[m.end(1):]
            print(line, file=fp, end='')

def years2str(years):
    return str(intspan(years)).replace(',', ', ')

def update_years2str(year_str, years=None):
    """
    Given a string of years of the form ``"2014, 2016-2017"``, update the
    string if necessary to include the given years (default: the current year).

    >>> update_years2str('2015', [2015])
    '2015'
    >>> update_years2str('2015', [2016])
    '2015-2016'
    >>> update_years2str('2015', [2017])
    '2015, 2017'
    >>> update_years2str('2014-2015', [2016])
    '2014-2016'
    >>> update_years2str('2013, 2015', [2016])
    '2013, 2015-2016'
    >>> update_years2str('2013, 2015', [2017, 2014])
    '2013-2015, 2017'
    """
    if years is None:
        years = [time.localtime().tm_year]
    yearspan = intspan(year_str)
    yearspan.update(years)
    return years2str(yearspan)
