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
This module contains BaseFuzzer, which implements most of the fuzzing logic
for both Server and Client fuzzing.

This module should not be overriden/referenced by entities outside of kitty,
as it is tightly coupled to the implementation of the Client and Server fuzzer,
and will probably be changed in the future.
'''
import sys
import time
import traceback
import shlex
from binascii import hexlify
from threading import Event
import docopt
from pkg_resources import get_distribution
from kitty.core import KittyException, KittyObject
from kitty.data.data_manager import DataManager, SessionInfo
from kitty.data.report import Report
from kitty.fuzzers.test_list import RangesList, StartEndList


def _flatten_dict_entry(orig_key, v):
    entries = []
    if isinstance(v, list):
        for i in range(len(v)):
            entries.extend(_flatten_dict_entry('%s[%s]' % (orig_key, i), v[i]))
    elif isinstance(v, dict):
        for k in v:
            entries.extend(_flatten_dict_entry('%s/%s' % (orig_key, k), v[k]))
    else:
        entries.append((orig_key, v))
    return entries


class _Configuration(object):

    def __init__(self, delay_secs, store_all_reports, session_file_name, max_failures):
        self.delay_secs = delay_secs
        self.store_all_reports = store_all_reports
        self.session_file_name = session_file_name
        self.max_failures = max_failures


def _get_current_version():
    package_name = 'kittyfuzzer'
    #
    # This is weird. I know that this is the way to get the version,
    # yet for some reason pylint complains about it.
    #
    current_version = get_distribution(package_name).version  # pylint: disable=maybe-no-member
    return current_version


class BaseFuzzer(KittyObject):
    '''
    Common members and logic for client and server fuzzers.
    This class should not be instantiated, only subclassed.
    '''

    def __init__(self, name='', logger=None, option_line=None):
        '''
        :param name: name of the object
        :param logger: logger for the object (default: None)
        :param option_line: cmd line options to the fuzzer (dafult: None)
        '''
        super(BaseFuzzer, self).__init__(name, logger)
        # session to fuzz
        self.model = None
        self.dataman = None
        self.session_info = SessionInfo()
        self.config = _Configuration(
            delay_secs=0,
            store_all_reports=False,
            session_file_name=None,
            max_failures=None,
        )
        # user interface
        self.user_interface = None
        # target
        self.target = None
        # event to implement pause / continue
        self._continue_event = Event()
        self._continue_event.set()
        self._fuzz_path = None
        self._fuzz_node = None
        self._last_payload = None
        self._skip_env_test = False
        self._in_environment_test = True
        self._started = False
        self._test_list = None
        self._handle_options(option_line)

    def _next_mutation(self):
        '''
        :return: True if mutated, False otherwise
        '''
        if self._keep_running():
            current_idx = self.model.current_index()
            self.session_info.current_index = current_idx
            next_idx = self._test_list.current()
            if next_idx is None:
                return False
            skip = next_idx - current_idx - 1
            if skip > 0:
                self.model.skip(skip)
            self._test_list.next()
            resp = self.model.mutate()
            return resp
        return False

    def _handle_options(self, option_line):
        '''
        Handle options from command line, in docopt style.
        This allows passing arguments to the fuzzer from the command line
        without the need to re-write it in each runner.

        :param option_line: string with the command line options to be parsed.
        '''
        if option_line is not None:
            usage = '''
            These are the options to the kitty fuzzer object, not the options to the runner.

            Usage:
                fuzzer [options] [-v ...]

            Options:
                -d --delay <delay>              delay between tests in secodes, float number
                -f --session <session-file>     session file name to use
                -n --no-env-test                don't perform environment test before the fuzzing session
                -r --retest <session-file>      retest failed/error tests from a session file
                -t --test-list <test-list>      a comma delimited test list string of the form "-10,12,15-20,30-"
                -v --verbose                    be more verbose in the log

            Removed options:
                end, start - use --test-list instead
            '''
            options = docopt.docopt(usage, shlex.split(option_line))

            # ranges
            if options['--retest']:
                retest_file = options['--retest']
                try:
                    test_list_str = self._get_test_list_from_session_file(retest_file)
                except Exception as ex:
                    raise KittyException('Failed to open session file (%s) for retesting: %s' % (retest_file, ex))
            else:
                test_list_str = options['--test-list']
            self._set_test_ranges(None, None, test_list_str)

            # session file
            session_file = options['--session']
            if session_file is not None:
                self.set_session_file(session_file)

            # delay between tests
            delay = options['--delay']
            if delay is not None:
                self.set_delay_between_tests(float(delay))

            # environment test
            skip_env_test = options['--no-env-test']
            if skip_env_test:
                self.set_skip_env_test(True)

            # verbosity
            verbosity = options['--verbose']
            self.set_verbosity(verbosity)

    def _get_test_list_from_session_file(self, session_file):
        dm = DataManager(session_file)
        dm.start()
        test_ids = dm.get_report_test_ids()
        if len(test_ids) == 0:
            raise KittyException('No failed tests in the session file %s' % session_file)
        test_list_str = ','.join('%s' % i for i in test_ids)
        dm.stop()
        return test_list_str

    def _set_test_ranges(self, start, end, test_list_str):
        if test_list_str and test_list_str.strip():
            self.set_test_list(test_list_str)
        else:
            s = 0 if start is None else int(start)
            e = end if end is None else int(end)
            self.set_range(s, e)

    def set_skip_env_test(self, skip_env_test=True):
        '''
        Set whether to skip the environment test.
        Call this if the environment test cannot pass
        and you prefer to start the tests without it.

        :param skip_env_test: skip the environment test (default: True)
        '''
        self._skip_env_test = skip_env_test

    def set_delay_duration(self, delay_duration):
        '''
        .. deprecated::
            use :func:`~kitty.fuzzers.base.BaseFuzzer.set_delay_between_tests`
        '''
        raise DeprecationWarning('API was changed, use set_delay_between_tests')

    def set_delay_between_tests(self, delay_secs):
        '''
        Set duration between tests

        :param delay_secs: delay between tests (in seconds)
        '''
        self.config.delay_secs = delay_secs
        return self

    def set_store_all_reports(self, store_all_reports):
        '''
        :param store_all_reports: should all reports be stored
        '''
        self.config.store_all_reports = store_all_reports
        return self

    def set_session_file(self, filename):
        '''
        Set session file name, to keep state between runs

        :param filename: session file name
        '''
        self.config.session_file_name = filename
        return self

    def set_model(self, model):
        '''
        Set the model to fuzz

        :type model: :class:`~kitty.model.high_level.base.BaseModel` or a subclass
        :param model: Model object to fuzz
        '''
        self.model = model
        if self.model:
            self.model.set_notification_handler(self)
            self.handle_stage_changed(model)
        return self

    def set_target(self, target):
        '''
        :param target: target object
        '''
        self.target = target
        if target:
            self.target.set_fuzzer(self)
        return self

    def set_max_failures(self, max_failures):
        '''
        :param max_failures: maximum failures before stopping the fuzzing session
        '''
        self.config.max_failures = max_failures
        return self

    def set_range(self, start_index=0, end_index=None):
        '''
        Set range of tests to run

        .. deprecated::
            use :func:`~kitty.fuzzers.base.BaseFuzzer.set_test_list`

        :param start_index: index to start at (default=0)
        :param end_index: index to end at(default=None)
        '''
        if end_index is not None:
            end_index += 1
        self._test_list = StartEndList(start_index, end_index)
        self.session_info.start_index = start_index
        self.session_info.current_index = 0
        self.session_info.end_index = end_index
        self.session_info.test_list_str = self._test_list.as_test_list_str()
        return self

    def set_test_list(self, test_list_str=''):
        '''
        :param test_list_str: listing of the test to execute

        The test list should be a comma-delimited string, and each element
        should be one of the following forms:

        '-x' - run from test 0 to test x
        'x-' - run from test x to the end
        'x' - run test x
        'x-y' - run from test x to test y

        To execute all tests, pass None or an empty string
        '''
        self.session_info.test_list_str = test_list_str
        self._test_list = RangesList(test_list_str)

    def set_interface(self, interface):
        '''
        :param interface: user interface
        '''
        self.user_interface = interface
        return self

    def _check_session_validity(self):
        current_version = _get_current_version()
        if current_version != self.session_info.kitty_version:
            raise KittyException('kitty version in stored session (%s) != current kitty version (%s)' % (
                current_version,
                self.session_info.kitty_version))
        model_hash = self.model.hash()
        if model_hash != self.session_info.data_model_hash:
            raise KittyException('data model hash in stored session(%s) != current data model hash (%s)' % (
                model_hash,
                self.session_info.data_model_hash
            ))

    def start(self):
        '''
        Start the fuzzing session

        If fuzzer already running, it will return immediatly
        '''
        if self._started:
            self.logger.warning('called while fuzzer is running. ignoring.')
            return
        self._started = True
        assert(self.model)
        assert(self.user_interface)
        assert(self.target)

        if self._load_session():
            self._check_session_validity()
            self._set_test_ranges(
                self.session_info.start_index,
                self.session_info.end_index,
                self.session_info.test_list_str
            )
        else:
            self.session_info.kitty_version = _get_current_version()
            # TODO: write hash for high level
            self.session_info.data_model_hash = self.model.hash()
        # if self.session_info.end_index is None:
        #     self.session_info.end_index = self.model.last_index()
        if self._test_list is None:
            self._test_list = StartEndList(0, self.model.num_mutations())
        else:
            self._test_list.set_last(self.model.last_index())

        list_count = self._test_list.get_count()
        self._test_list.skip(list_count - 1)
        self.session_info.end_index = self._test_list.current()
        self._test_list.reset()
        self._store_session()
        self._test_list.skip(self.session_info.current_index)
        self.session_info.test_list_str = self._test_list.as_test_list_str()

        self._set_signal_handler()
        self.user_interface.set_data_provider(self.dataman)
        self.user_interface.set_continue_event(self._continue_event)
        self.user_interface.start()

        self.session_info.start_time = time.time()
        try:
            self._start_message()
            self.target.setup()
            start_from = self.session_info.current_index
            if self._skip_env_test:
                self.logger.info('Skipping environment test')
            else:
                self.logger.info('Performing environment test')
                self._test_environment()
            self._in_environment_test = False
            self._test_list.reset()
            self._test_list.skip(start_from)
            self.session_info.current_index = start_from
            self.model.skip(self._test_list.current())
            self._start()
            return True
        except Exception as e:
            self.logger.error('Error occurred while fuzzing: %s', repr(e))
            self.logger.error(traceback.format_exc())
            return False

    def handle_stage_changed(self, model):
        '''
        handle a stage change in the data model

        :param model: the data model that was changed
        '''
        stages = model.get_stages()
        if self.dataman:
            self.dataman.set('stages', stages)

    def _test_environment(self):
        '''
        Test that the environment is ready to run.
        Should be implemented by subclass
        '''
        raise NotImplementedError('should be implemented by subclass')

    def _start(self):
        self.not_implemented('_start')

    def _update_test_info(self):
        test_info = self.model.get_test_info()
        self.dataman.set('test_info', test_info)
        template_info = self.model.get_template_info()
        self.dataman.set('template_info', template_info)

    def _pre_test(self):
        self._update_test_info()
        self.session_info.current_index = self._test_list.current()
        self.target.pre_test(self.model.current_index())

    def _post_test(self):
        '''
        :return: True if test failed
        '''
        failure_detected = False
        self.target.post_test(self.model.current_index())
        report = self._get_report()
        status = report.get_status()
        if self._in_environment_test:
            return status != Report.PASSED
        if status != Report.PASSED:
            self._store_report(report)
            self.user_interface.failure_detected()
            failure_detected = True
            self.logger.warning('!! Failure detected !!')
        elif self.config.store_all_reports:
            self._store_report(report)
        if failure_detected:
            self.session_info.failure_count += 1
        self._store_session()
        if self.config.delay_secs:
            self.logger.debug('delaying for %f seconds', self.config.delay_secs)
            time.sleep(self.config.delay_secs)
        return failure_detected

    def _get_report(self):
        report = self.target.get_report()
        return report

    def _start_message(self):
        self.logger.info(
            '''
                 --------------------------------------------------
                 Starting fuzzing session
                 Target: %s
                 UI: %s
                 Log: %s

                 Total possible mutation count: %d
                 --------------------------------------------------
                                 Happy hacking
                 --------------------------------------------------
            ''',
            self.target.get_description(),
            self.user_interface.get_description(),
            self.get_log_file_name(),
            self.model.num_mutations(),
        )

    def _end_message(self):
        tested = self._test_list.get_progress()
        self.logger.info(
            '''
                         --------------------------------------------------
                         Finished fuzzing session
                         Target: %s

                         Tested %d mutation%s
                         Failure count: %d
                         --------------------------------------------------
            ''',
            self.target.get_description(),
            tested,
            's' if tested > 1 else '',
            self.session_info.failure_count
        )

    def _test_info(self):
        fuzz_node_info = self.model.get_test_info()
        self.logger.info('Current test: %s' % self.model.current_index())
        self.logger.debug('----------------------------------------------')
        keys = sorted(fuzz_node_info.keys())
        keys = [k for k in keys if k.startswith('node/field')]
        keys = [k for k in keys if not isinstance(fuzz_node_info[k], bool)]
        key_max_len = 0
        for key in keys:
            if len(key) > key_max_len:
                key_max_len = len(str(key))
        for k in keys:
            v = str(fuzz_node_info[k])
            k = str(k)
            pad = ' ' * (key_max_len - len(k) + 1)
            if len(v) > 70:
                v = v[:70] + '...'
            self.logger.debug('%s:%s%s' % (k, pad, v))
        self.logger.debug('----------------------------------------------')

    def _check_pause(self):
        if not self._continue_event.is_set():
            self.logger.info('fuzzer paused, waiting for resume command from user')
            self._continue_event.wait()
            self.logger.info('resume command received, continue running')

    def stop(self):
        '''
        stop the fuzzing session
        '''
        assert(self.model)
        assert(self.user_interface)
        assert(self.target)
        self.user_interface.stop()
        self.target.teardown()
        self.dataman.submit_task(None)
        self._un_set_signal_handler()

    def _store_report(self, report):
        self.logger.debug('<in>')
        report.add('test_number', self.model.current_index())
        report.add('fuzz_path', self.model.get_sequence_str())
        test_info = self.model.get_test_info()
        data_model_report = Report(name='Data Model')
        for k, v in test_info.items():
            new_entries = _flatten_dict_entry(k, v)
            for (k_, v_) in new_entries:
                data_model_report.add(k_, v_)
        report.add(data_model_report.get_name(), data_model_report)
        payload = self._last_payload
        if payload is not None:
            data_report = Report('payload')
            data_report.add('raw', payload)
            data_report.add('hex', hexlify(payload).decode())
            data_report.add('length', len(payload))
            report.add('payload', data_report)
        else:
            report.add('payload', None)

        self.dataman.store_report(report, self.model.current_index())
        self.dataman.get_report_by_id(self.model.current_index())

    def _store_session(self):
        self._set_session_info()

    def _get_session_info(self):
        info = self.dataman.get_session_info()
        return info

    def _get_test_info(self):
        info = self.dataman.get('test_info')
        return info

    def _set_session_info(self):
        self.dataman.set_session_info(self.session_info)
        self.dataman.set('fuzzer_name', self.get_name())
        self.dataman.set('session_file_name', self.config.session_file_name)

    def _load_session(self):
        if not self.config.session_file_name:
            self.config.session_file_name = ':memory:'
        self.dataman = DataManager(self.config.session_file_name)
        self.dataman.start()
        if self.model:
            self.handle_stage_changed(self.model)
        self.dataman.set('log_file_name', self.get_log_file_name())
        info = self._get_session_info()
        if info:
            self.logger.info('Loaded session from DB')
            self.session_info = info
            return True
        self.logger.info('No session loaded')
        self._set_session_info()
        return False

    def _exit_now(self, dummy1, dummy2):
        self.stop()
        sys.exit(0)

    def _keep_running(self):
        '''
        Should we still fuzz??
        '''
        if self.config.max_failures:
            if self.session_info.failure_count >= self.config.max_failures:
                return False
        return self._test_list.current() is not None

    def _set_signal_handler(self):
        '''
        Replace the signal handler with self._exit_now
        '''
        import signal
        signal.signal(signal.SIGINT, self._exit_now)

    @classmethod
    def _un_set_signal_handler(cls):
        '''
        Set the default signal handler
        '''
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)
