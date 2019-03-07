#!/usr/bin/env python
# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Kitty.
#
# Kitty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Kitty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitty.  If not, see <http://www.gnu.org/licenses/>.
'''
Usage:
    kitty_web_client.py (info [-v]|pause|resume) [--host <hostname>] [--port <port>]
    kitty_web_client.py reports store <folder> [--host <hostname>] [--port <port>]
    kitty_web_client.py reports show <file> ...

Retrieve and parse kitty status and reports from a kitty web server

Options:
    -v --verbose            verbose information
    -h --host <hostname>    kitty web server host [default: localhost]
    -p --port <port>        kitty web server port [default: 26000]
'''
import os
import json
from base64 import b64decode
from binascii import hexlify
import requests
import docopt


class KittyWebClientApi(object):

    def __init__(self, host, port):
        '''
        :param host: server hostname
        :param port: server port
        :param reports_dir: directory to store reports
        '''
        self.url = 'http://%(host)s:%(port)s' % {'host': host, 'port': port}

    def get_stats(self):
        '''
        Get kitty stats as a dictionary
        '''
        resp = requests.get('%s/api/stats.json' % self.url)
        assert(resp.status_code == 200)
        return resp.json()

    def get_report_list(self):
        '''
        Get list of report ids
        '''
        return self.get_stats()['reports_extended']

    def get_reports(self, report_ids):
        '''
        Get reports by list of ids
        :param report_ids: list of reports ids
        :return dictionary of id/report (json string)
        '''
        res = {}
        for rid in report_ids:
            print('Fetching report %d' % rid)
            resp = requests.get('%s/api/report?report_id=%d' % (self.url, rid))
            if resp.status_code != 200:
                print('[!] failed to fetch report %d' % rid)
            else:
                res[rid] = resp.text
        return res

    def pause(self):
        requests.get('%s/api/action/pause' % (self.url))

    def resume(self):
        requests.get('%s/api/action/resume' % (self.url))


def cmd_report_store(options, web):
    folder = options['<folder>']
    folder = os.path.join('.', folder)
    if not os.path.exists(folder):
        os.mkdir(folder)
    ids = [x[0] for x in web.get_report_list()]
    reports = web.get_reports(ids)
    for (rid, report) in reports.items():
        with open(os.path.join(folder, 'report_%d.json' % (rid)), 'w') as f:
            f.write(report)


def cmd_report_show(options):
    filenames = options['<file>']
    for filename in filenames:
        with open(filename, 'r') as f:
            report = json.load(f)['report']
            print_report(report, depth=0)


def _pad(depth, with_key):
    if depth > 0:
        if with_key:
            return '    ' * (depth - 1) + '+---'
        return '    ' * (depth)
    return ''


def indent_print(depth, key, val=None):
    if val is None:
        print(_pad(depth, True) + key)
    else:
        pre_len = len(key)
        first = True
        for line in val.split('\n'):
            print(_pad(depth, with_key=first) + key + line)
            if first:
                key = ' ' * pre_len
                first = False


def format_key(k):
    return k.replace('_', ' ')


def print_entry(k, v, depth, decode_str):
    if isinstance(v, list):
        indent_print(depth, '%-20s' % (k + ':'))
        for i in range(len(v)):
            print_entry('%s' % i, v, depth + 1, decode_str)
    elif isinstance(v, dict):
        indent_print(depth, '%-20s' % (k + ':'))
        for subk in sorted(v):
            print_entry(subk, v[subk], depth + 1, decode_str)
    else:
        print_key_val(k, v, depth, decode_str)


def print_key_val(k, val, depth, decode_str):
    if isinstance(val, str) and decode_str:
        try:
            val = b64decode(val).decode()
        except:
            pass
    key = format_key(k)
    try:
        indent_print(depth, '%-20s' % (key + ':'), '%s' % val)
    except UnicodeDecodeError:
        indent_print(depth, '%-20s' % (key + ':'), '%s' % hexlify(val).decode())


def print_report(report, depth):
    # next two fields should not be printed as normal fields
    name = b64decode(report['name']).decode()
    del report['name']
    sub_reports = report['sub_reports']
    del report['sub_reports']
    # print report header
    indent_print(depth, '***** Report: %s *****' % name)
    # print entries (excluding sub-reports)
    for k in sorted(report.keys()):
        if k not in sub_reports:
            val = report[k]
            print_entry(k, val, depth, True)
    print('')
    # print sub-reports
    for sr in sorted(sub_reports):
        print_report(report[sr], depth)


def cmd_info(options, web):
    resp = web.get_stats()

    print('--- Stats ---')
    stats = resp['stats']
    for k, v in stats.items():
        print('%s: %s' % (k, v))
    print('')

    print('--- Current Test Info ---')
    info = resp['current_test']
    # max_len = max(len(k) for k in info.keys())
    for k, v in sorted(info.items()):
        print_entry(k, v, 0, False)
        # pad = ' ' * (max_len - len(k))
        # print('%s:%s %s' % (k, pad, v))

    if options['--verbose']:
        reports = resp['reports_extended']
        print('')
        print('--- Report list ---')
        print('\n'.join('%-10s %-10s %s' % tuple(report) for report in reports))


def _main():
    options = docopt.docopt(__doc__)
    web = KittyWebClientApi(options['--host'], int(options['--port']))
    if options['reports']:
        if options['store']:
            cmd_report_store(options, web)
        elif options['show']:
            cmd_report_show(options)
    elif options['info']:
        cmd_info(options, web)
    elif options['pause']:
        web.pause()
    elif options['resume']:
        web.resume()


if __name__ == '__main__':
    _main()
