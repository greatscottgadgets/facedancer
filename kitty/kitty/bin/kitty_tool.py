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
Tools for testing and manipulating kitty templates.

Usage:
    kitty-tool generate [options] <FILE> <TEMPLATE> ...
    kitty-tool list <FILE>
    kitty-tool --version

Commands:
    generate    generate files with mutated payload
    list        list templates in a file

Options:
    <FILE>                  python file that contains the template
    <TEMPLATE>              template name(s) to generate files from
    --out -o OUTDIR         output directory for the generated mutations [default: out]
    --skip -s SKIP          how many mutations to skip [default: 0]
    --count -c COUNT        end index to generate
    --field-path -p FIELDPATH   generate mutations only for the field with the given path
    --verbose -v            verbose output
    --filename-format -f FORMAT  format for generated file names [default: %(template)s.%(index)s.bin]
    --version               print version and exit
    --help -h               print this help and exit

File name formats:
    You can control the name of an output file by giving a filename format,
    it follows python's dictionary format string.
    The available keywords are:
        template - the template name
        index - the template index
'''
import os
import sys
import types
import logging
from pkg_resources import get_distribution
from json import dumps
import docopt
import traceback
from kitty.model import Template


def get_logger(opts):
    logger = logging.getLogger('kitty-tool')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    return logger


class FileIterator(object):

    def __init__(self, filename, handler, logger):
        self.filename = filename
        self.handler = handler
        self.logger = logger

    def check_file(self):
        if not os.path.exists(self.filename):
            raise Exception('File %s does not exist' % self.filename)
        elif not self.filename.endswith('.py'):
            raise Exception('File %s is not python' % self.filename)

    def iterate(self):
        self.check_file()
        self.handler.start()
        dirpath, filename = os.path.split(self.filename)
        modulename = filename[:-3]
        if dirpath in sys.path:
            sys.path.remove(dirpath)
        sys.path.insert(0, dirpath)
        module = __import__(modulename)
        member_names = dir(module)
        for name in member_names:
            attr = getattr(module, name)
            if isinstance(attr, Template):
                self.handler.handle(attr)
            elif isinstance(attr, list):
                for mem in attr:
                    if isinstance(mem, Template):
                        self.handler.handle(mem)
            elif isinstance(attr, dict):
                for k in attr:
                    if isinstance(attr[k], Template):
                        self.handler.handle(attr[k])


class Handler(object):

    def __init__(self, opts, logger):
        self.opts = opts
        self.logger = logger

    def start(self):
        pass

    def handle(self, template):
        pass


def to_int(val, name):
    if val is None:
        return val
    try:
        return int(val)
    except:
        raise Exception('%s should be a number' % name)


class FileGeneratorHandler(Handler):

    def __init__(self, opts, logger):
        super(FileGeneratorHandler, self).__init__(opts, logger)
        self.outdir = opts['--out'] or 'out'
        if opts['--skip'] is None:
            self.skip = '0'
        self.skip = to_int(opts['--skip'], 'skip')
        self.count = to_int(opts['--count'], 'count')
        self.template_names = opts['<TEMPLATE>']
        self.filename_format = opts['--filename-format']
        try:
            self.filename_format % {
                'template': 'hello',
                'index': 1
            }
        except:
            raise Exception('invalid filename template: %s' % (self.filename_format))

    def start(self):
        if os.path.exists(self.outdir):
            raise Exception('cannot create directory %s, already exists' % self.outdir)
        os.mkdir(self.outdir)

    def handle(self, template):
        self.template = template
        template_name = template.get_name()
        if template_name in self.template_names:
            self.logger.info('Generating mutation files from template %s into %s' % (template_name, os.path.abspath(self.outdir)))
            self._set_current_template_params(template)
            self.logger.info('Mutation range: %s-%s (total: %d)' % (self.skip, self.end_index, self.end_index - self.skip + 1))
            self._progress_init()
            while template.mutate():
                template_filename = self.filename_format % {'template': template_name, 'index': template._current_index}
                self._store_template(template, template_filename)
                metadata_filename = template_filename + '.metadata'
                info = template.get_info()
                self._store_metadata(info, metadata_filename)
                self._progress_print(template._current_index, info)
                if template._current_index >= self.end_index:
                    break
            self._progress_finalize()

    def _set_current_template_params(self, template):
        template.skip(self.skip)
        self.end_index = template.num_mutations() if not self.count else self.skip + self.count
        self.end_index = min(self.end_index, template.num_mutations()) - 1
        if self.end_index < 0:
            raise Exception('No mutations to generate, are you sure about the count ??')
        if self.skip > template.num_mutations():
            raise Exception('No mutations to generate, you skipped over the entire template')

    def _store_template(self, template, filename):
        with open(os.path.join(self.outdir, filename), 'wb') as f:
            f.write(template.render().tobytes())

    def _store_metadata(self, info, filename):
        with open(os.path.join(self.outdir, filename), 'wb') as f:
            f.write(dumps(info, indent=4, sort_keys=True))

    def _progress_init(self):
        self.total = (self.end_index - self.skip)
        self.step = 100.0 / self.total
        self.max_line_length = 0

    def _progress_print(self, current_index, info):
        tests_left = (self.end_index - current_index)
        percent = int((self.total - tests_left) * self.step)
        out_line = ''
        out_line += '\r%3d%%' % (percent)
        out_line += ' %d/%d' % (current_index - self.skip + 1, self.end_index - self.skip + 1)
        if 'field/path' in info:
            out_line += ' %s' % (info['field/path'])
        if len(out_line) > self.max_line_length:
            max_line_length = len(out_line)
        else:
            max_line_length = self.max_line_length
        out_line += ' ' * (max_line_length - len(out_line))
        sys.stdout.write(out_line)
        sys.stdout.flush()

    def _progress_finalize(self):
        sys.stdout.write('\n')
        sys.stdout.flush()


class ListHandler(Handler):

    def handle(self, template):
        self.logger.info('%-80s %s' % (template.get_name(), template.num_mutations()))


def _main():
    opts = docopt.docopt(__doc__, version=get_distribution('kittyfuzzer').version)
    logger = get_logger(opts)
    try:
        if opts['generate'] or opts['list']:
            if opts['generate']:
                handler = FileGeneratorHandler(opts, logger)
            elif opts['list']:
                handler = ListHandler(opts, logger)
            file_iter = FileIterator(opts['<FILE>'], handler, logger)
            file_iter.iterate()
    except Exception as ex:
        if opts['--verbose']:
            logger.error(traceback.format_exc())
        logger.error('Error: %s' % ex)
        sys.exit(1)


if __name__ == '__main__':
    _main()
