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
    kitty_template_tester.py [--fast] [--tree] [--verbose] <FILE> ...

This tool mutates and renders templates in a file, making sure there are no
syntax issues in the templates.
It doesn't prove that the data model is correct, only checks that the it is
a valid model

Options:
    <FILE>      python file that contains templates in dictionaries, lists or globals
    --fast      only import, don't run all mutations
    --tree      print fields tree of the template instead of mutating it
    --verbose   print full call stack upon exception
'''
import os
import sys
import traceback
import docopt
from pkg_resources import get_distribution
from kitty.model import Template


class TemplateProcessor(object):

    def __init__(self):
        self.verbose = False

    def process(self, t):
        pass


class TemplateTreePrinter(TemplateProcessor):

    def _pad(self):
        return '  ' * self.depth

    def _print_structure(self, structure):
        print('%s%s(name="%s")' % (self._pad(), structure['field_type'], structure['name']))
        if 'fields' in structure:
            self.depth += 1
            for field in structure['fields']:
                self._print_structure(field)
            self.depth -= 1

    def process(self, t):
        self.depth = 0
        structure = t.get_structure()
        self._print_structure(structure)


class TemplateTester(TemplateProcessor):

    def __init__(self, fast):
        super(TemplateProcessor, self).__init__()
        self._fast = fast

    def process(self, t):
        print('[mutation count: %d]' % t.num_mutations())
        t.render()
        if not self._fast:
            count = 0
            while t.mutate():
                count += 1
                t.render()
            t.reset()
            count = 0
            while t.mutate():
                count += 1
                t.render()
            t.reset()


def validate_file(f):
    valid = False
    if not os.path.exists(f):
        print('File %s does not exist' % f)
    elif not f.endswith('.py'):
        print('File %s is not python' % f)
    else:
        valid = True
    return valid


def validate_files(files):
    valid = True
    for f in files:
        valid = valid and validate_file(f)
    if not valid:
        raise Exception('Failed at validating files')
    return valid


def test_if_template(obj, description, processor):
    if isinstance(obj, Template):
        print('Template %s: %s' % (obj.get_name(), description))
        try:
            processor.process(obj)
            print('[PASS]')
        except Exception as e:
            print('[FAIL]')
            if processor.verbose:
                print(traceback.format_exc())
            else:
                print(e)


def process_file(f, processor):
    try:
        dirpath, filename = os.path.split(f)
        modulename = filename[:-3]
        if dirpath in sys.path:
            sys.path.remove(dirpath)
        sys.path.insert(0, dirpath)
        module = __import__(modulename)
        member_names = dir(module)
        print('Testing file %s' % f)
        for name in member_names:
            try:
                attr = getattr(module, name)
                if isinstance(attr, Template):
                    description = '(member name %s)' % name
                    test_if_template(attr, description, processor)
                elif isinstance(attr, list):
                    for mem in attr:
                        description = '(element in list %s)' % name
                        test_if_template(mem, description, processor)
                elif isinstance(attr, dict):
                    for k in attr:
                        description = '(%s[%s])' % (name, k)
                        test_if_template(attr[k], description, processor)
                else:
                    attr = None
            except Exception as e:
                print('Exception when testing member %s' % name)
                if processor.verbose:
                    print(traceback.format_exc())
    except Exception as e:
        print('Exception when processing file %s: %s' % (f, e))
        if processor.verbose:
            print(traceback.format_exc())


def _main():
    print('kitty version: %s' % get_distribution('kittyfuzzer').version)
    opts = docopt.docopt(__doc__)
    files = opts['<FILE>']
    fast = opts['--fast']
    verbose = opts['--verbose']
    if opts['--tree']:
        processor = TemplateTreePrinter()
    else:
        processor = TemplateTester(fast)
    processor.verbose = verbose
    try:
        validate_files(files)
        for f in files:
            process_file(f, processor)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    _main()
