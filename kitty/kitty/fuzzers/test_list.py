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
Managers for the test list used by the fuzzer
'''
import re
from kitty.core import KittyException


class StartEndList(object):

    def __init__(self, start, end):
        self._start = start
        self._end = end
        self._current = self._start

    def set_last(self, last):
        if self.open_ended() or (self._end > last):
            self._end = last + 1

    def next(self):
        if self._current < self._end:
            self._current += 1

    def current(self):
        if self._current < self._end:
            return self._current
        return None

    def reset(self):
        self._current = self._start

    def skip(self, count):
        if count < self._end - self._current:
            self._current += count
            skipped = count
        else:
            skipped = self._end - self._current
            self._current = self._end
        return skipped

    def get_count(self):
        return self._end - self._start

    def get_progress(self):
        if self.current():
            return self._current - self._start
        else:
            return self.get_count()

    def as_test_list_str(self):
        res = '%d-' % self._start
        if not self.open_ended():
            res += '%d' % (self._end - 1)
        return res

    def open_ended(self):
        return self._end is None


class RangesList(object):

    def __init__(self, ranges_str):
        self._ranges_str = ranges_str
        self._lists = []
        self._idx = 0
        self._list_idx = 0
        self._count = None
        self._parse()

    def _parse(self):
        '''
        Crazy function to check and parse the range list string
        '''
        if not self._ranges_str:
            self._lists = [StartEndList(0, None)]
        else:
            lists = []
            p_single = re.compile(r'(\d+)$')
            p_open_left = re.compile(r'-(\d+)$')
            p_open_right = re.compile(r'(\d+)-$')
            p_closed = re.compile(r'(\d+)-(\d+)$')
            for entry in self._ranges_str.split(','):
                entry = entry.strip()

                # single number
                match = p_single.match(entry)
                if match:
                    num = int(match.groups()[0])
                    lists.append(StartEndList(num, num + 1))
                    continue

                # open left
                match = p_open_left.match(entry)
                if match:
                    end = int(match.groups()[0])
                    lists.append(StartEndList(0, end + 1))
                    continue

                # open right
                match = p_open_right.match(entry)
                if match:
                    start = int(match.groups()[0])
                    self._open_end_start = start
                    lists.append(StartEndList(start, None))
                    continue

                # closed range
                match = p_closed.match(entry)
                if match:
                    start = int(match.groups()[0])
                    end = int(match.groups()[1])
                    lists.append(StartEndList(start, end + 1))
                    continue

                # invalid expression
                raise KittyException('Invalid range found: %s' % entry)

            lists = sorted(lists, key=lambda x: x._start)
            for i in range(len(lists) - 1):
                if lists[i]._end is None:
                    # there is an open end which is not the last in our lists
                    # this is a clear overlap with the last one ...
                    raise KittyException('Overlapping ranges in range list')
                elif lists[i]._end > lists[i + 1]._start:
                    raise KittyException('Overlapping ranges in range list')
            self._lists = lists

    def set_last(self, last):
        exceeds = False
        last_list = self._lists[-1]
        if last <= last_list._start:
            exceeds = True
        elif last_list.open_ended():
            last_list.set_last(last)
        if exceeds:
            raise KittyException('Specified test range exceeds the maximum mutation count')

    def next(self):
        if self._idx < self.get_count():
            if self._list_idx < len(self._lists):
                curr_list = self._lists[self._list_idx]
                curr_list.next()
                if curr_list.current() is None:
                    self._list_idx += 1
        self._idx += 1

    def current(self):
        if self._idx < self.get_count():
            return self._lists[self._list_idx].current()
        return None

    def reset(self):
        self._idx = 0
        self._list_idx = 0
        for l in self._lists:
            l.reset()

    def skip(self, count):
        while count > 0:
            skipped = self._lists[self._list_idx].skip(count)
            self._idx += skipped
            count -= skipped
            if count > 0:
                self._list_idx += 1

    def get_count(self):
        if self._count is None:
            self._count = sum(l.get_count() for l in self._lists)
        return self._count

    def get_progress(self):
        if self.current():
            return self._current
        else:
            return self.get_count()

    def as_test_list_str(self):
        return self._ranges_str
