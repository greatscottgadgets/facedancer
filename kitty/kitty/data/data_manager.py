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
This module is usde to store the fuzzing session related data.
It provides both means of communications between the fuzzer and the user
interface, and persistent storage of the fuzzing session results.
'''
import sqlite3
import sys
import zlib
import traceback
from base64 import b64decode, b64encode
from threading import Event, Thread
from kitty.core import KittyObject
from kitty.data.report import Report
if sys.version_info >= (3,):
    from queue import Queue
    import _pickle as cPickle
else:
    import cPickle
    from Queue import Queue


class DataManagerTask(object):
    '''
    Task to be performed in the :class:`~kitty.data.data_manager.DataManager`
    context
    '''

    def __init__(self, task, *args):
        '''
        :type task: function(:class:`~kitty.data.data_manager.DataManager`) -> object
        :param task: task to be performed
        '''
        self._event = Event()
        self._result = None
        self._task = task
        self._args = args
        self._exception = None

    def execute(self, dataman):
        '''
        run the task

        :type dataman: :class:`~kitty.data.data_manager.DataManager`
        :param dataman: the executing data manager
        '''
        self._event.clear()
        try:
            self._result = self._task(dataman, *self._args)
        #
        # We are going to re-throw this exception from get_results,
        # so we are doing such a general eception handling at the point.
        # however, we do want to print it here as well
        #
        except Exception as ex:  # pylint: disable=W0703
            self._exception = ex
            KittyObject.get_logger().error(traceback.format_exc())
        self._event.set()

    def get_results(self):
        '''
        :return: result from running the task
        '''
        self._event.wait()
        if self._exception is not None:
            #
            # Well... rethrownig the exception caught in execute
            # but on the caller thread
            #
            raise self._exception  # pylint: disable=E0702
        return self._result


def synced(func):
    '''
    Decorator for functions that should be called synchronously from another thread

    :param func: function to call
    '''

    def wrapper(self, *args, **kwargs):
        '''
        Actual wrapper for the synchronous function
        '''
        task = DataManagerTask(func, *args, **kwargs)
        self.submit_task(task)
        return task.get_results()
    return wrapper


class DataManager(Thread):
    '''
    Manages data on a dedicated thread. All calls to it should be done by
    submitting DataManagerTask

    :example:

        ::

            dataman = DataManager('fuzz_session.sqlite`)
            dataman.start()
            def get_session_info(manager):
                return manager.get_session_info_manager().get_session_info()
            get_info_task = DataManagerTask(get_session_info)
            dataman.submit_task(get_info_task)
            session_info = get_info_task.get_results()
    '''

    def __init__(self, dbname):
        '''
        :param dbname: database name for storing the data
        '''
        super(DataManager, self).__init__()
        self._queue = Queue()
        self._dbname = dbname
        self._connection = None
        self._cursor = None
        self._session_info = None
        self._reports = None
        self._volatile_data = {}
        self._stopped_event = Event()

    def run(self):
        '''
        thread function
        '''
        self._stopped_event.clear()
        self.open()
        while True:
            task = self._queue.get()
            if task is None:
                break
            task.execute(self)
        self.close()
        self._stopped_event.set()

    def submit_task(self, task):
        '''
        submit a task to the data manager, to be proccessed in the DataManager context

        :type task: :class:`~kitty.data.data_manager.DataManagerTask`
        :param task: task to perform
        '''
        self._queue.put(task)
        return task

    def open(self):
        '''
        open the database
        '''
        self._connection = sqlite3.connect(self._dbname)
        self._cursor = self._connection.cursor()
        self._session_info = SessionInfoTable(self._connection, self._cursor)
        self._reports = ReportsTable(self._connection, self._cursor)

    def close(self):
        '''
        close the database connection
        '''
        self._connection.close()

    def stop(self):
        '''
        Stop the data manager
        '''
        self.submit_task(None)
        self._stopped_event.wait()

    @synced
    def get_session_info_manager(self):
        '''
        :rtype: :class:`~kitty.data.data_manager.SessionInfoTable`
        :return: session info manager
        '''
        return self._session_info

    @synced
    def get_session_info(self):
        '''
        :return: current session info
        '''
        return self._session_info.get_session_info()

    @synced
    def set_session_info(self, info):
        '''
        :type info: :class:`~kitty.data.data_manager.SessionInfo`
        :param info: info to set
        '''
        self._session_info.set_session_info(info)

    @synced
    def get_reports_manager(self):
        '''
        :rtype: :class:`~kitty.data.data_manager.ReportsTable`
        :return: reports manager
        '''
        return self._reports

    @synced
    def get_report_test_ids(self):
        '''
        :return: list of report ids
        '''
        return self._reports.get_report_test_ids()

    @synced
    def get_report_list(self):
        '''
        :return: list of tuples [(report id, status, reason) ..]
        '''
        return self._reports.get_report_list()

    @synced
    def get_report_by_id(self, report_id):
        '''
        :param report_id: if of report to get
        :rtype: :class:`~kitty.data.report.Report`
        :return: report object
        '''
        return self._reports.get(report_id)

    @synced
    def store_report(self, report, test_id):
        '''
        :param report: the report to store
        :param test_id: the id of the test reported
        :return: report id
        '''
        self._reports.store(report, test_id)

    @synced
    def set(self, key, data):
        '''
        set arbitrary data by key in volatile memory

        :param key: key of the data
        :param data: data to be stored
        '''
        if isinstance(data, dict):
            self._volatile_data[key] = {k: v for (k, v) in data.items()}
        else:
            self._volatile_data[key] = data

    @synced
    def get(self, key):
        '''
        get arbitrary data by key from volatile memory

        :param key: key of the data
        :return: the data
        '''
        return self._volatile_data.get(key, None)


class Table(object):
    '''
    Base class for data manager tables
    '''

    __TABLE_FIELDS__ = []
    __TABLE_NAME__ = None

    def __init__(self, connection, cursor):
        '''
        :param connection: the database connection
        :param cursor: the cursor for the database
        '''
        self._connection = connection
        self._cursor = cursor
        self._name = type(self).__TABLE_NAME__
        self._fields = type(self).__TABLE_FIELDS__
        self._create_table()

    def _create_table(self):
        '''
        create the current table if not exists
        '''
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS %(name)s ( %(fields)s )
        ''' % {
            'name': self._name,
            'fields': ','.join('%s %s' % (k, v) for (k, v) in self._fields)
        })
        self._connection.commit()

    def select(self, to_select, where=None, sql_params=None):
        '''
        select db entries

        :param to_select: string of fields to select
        :param where: where clause (default: None)
        :param sql_params: params for the where clause
        '''
        if sql_params is None:
            sql_params = []
        query = '''
        SELECT %s FROM %s
        ''' % (to_select, self._name)
        if where:
            query = '%s WHERE %s' % (query, where)
        return self._cursor.execute(query, tuple(sql_params))

    def row_to_dict(self, row):
        '''
        translate a row of the current table to dictionary

        :param row: a row of the current table (selected with \\*)
        :return: dictionary of all fields
        '''
        res = {}
        for i in range(len(self._fields)):
            res[self._fields[i][0]] = row[i]
        return res

    def update(self, field_dict, where_clause=None):
        '''
        update db entry

        :param field_dict: dictionary of fields and values
        :param where_clause: where clause for the update
        '''
        query = '''
        UPDATE %s SET %s
        ''' % (
            self._name,
            ','.join('%s=:%s' % (k, k) for k in field_dict)
        )
        if where_clause:
            query += ' WHERE %s' % (where_clause)
        self._cursor.execute(query, field_dict)
        self._connection.commit()

    def insert(self, fields, values):
        '''
        insert new db entry

        :param fields: list of fields to insert
        :param values: list of values to insert
        :return: row id of the new row
        '''
        if fields:
            _fields = ' (%s) ' % ','.join(fields)
        else:
            _fields = ''
        _values = ','.join('?' * len(values))
        query = '''
        INSERT INTO %s %s VALUES (%s)
        ''' % (self._name, _fields, _values)
        self._cursor.execute(query, tuple(values))
        self._connection.commit()
        return self._cursor.lastrowid


class ReportsTable(Table):
    '''
    Table for storing the reports
    '''

    __TABLE_NAME__ = 'reports'
    __TABLE_FIELDS__ = [
        ('id', 'INTEGER PRIMARY KEY'),
        ('test_id', 'INT'),
        ('content', 'BLOB'),
        ('status', 'BLOB'),
        ('reason', 'BLOB'),
    ]

    def __init__(self, connection, cursor):
        '''
        :param connection: the database connection
        :param cursor: the cursor for the database
        '''
        super(ReportsTable, self).__init__(connection, cursor)

    def store(self, report, test_id):
        '''
        :param report: the report to store
        :param test_id: the id of the test reported
        :return: report id
        '''
        report_d = report.to_dict()
        content = self._serialize_dict(report_d)
        report_id = self.insert(
            ['test_id', 'content', 'status', 'reason'],
            [test_id, content, report.get_status(), report.get('reason')],
        )
        return report_id

    def get(self, test_id):
        '''
        get report by the test id

        :param test_id: test id
        :return: Report object
        '''
        self.select('*', 'test_id=?', [test_id])
        row = self._cursor.fetchone()
        if not row:
            raise KeyError('No report with test id %s in the DB' % test_id)

        values = self.row_to_dict(row)
        content = self._deserialize_dict(values['content'])
        return Report.from_dict(content)

    def get_report_test_ids(self):
        '''
        :return: ids of test reports
        '''
        self.select('test_id')
        res = []
        for row in self._cursor.fetchall():
            res.append(row[0])
        return res

    def get_report_list(self):
        '''
        :return: ids of test reports
        '''
        self.select('test_id, status, reason')
        res = []
        for row in self._cursor.fetchall():
            res.append((row[0], row[1], row[2]))
        return res

    @classmethod
    def _serialize_dict(cls, data):
        '''
        serializes a dictionary

        :param data: data to serialize
        '''
        return b64encode(zlib.compress(cPickle.dumps(data, protocol=2))).decode()

    @classmethod
    def _deserialize_dict(cls, data):
        '''
        deserializes a dictionary

        :param data: data to deserialize
        '''
        return cPickle.loads(zlib.decompress(b64decode(data.encode())))


class SessionInfoTable(Table):
    '''
    Table for storing the session info
    '''

    __TABLE_NAME__ = 'info'
    __TABLE_FIELDS__ = [
        ('start_time', 'INT'),
        ('start_index', 'INT'),
        ('end_index', 'INT'),
        ('current_index', 'INT'),
        ('failure_count', 'INT'),
        ('kitty_version', 'BLOB'),
        ('data_model_hash', 'INT'),
        ('test_list_str', 'BLOB')
    ]

    def __init__(self, connection, cursor):
        '''
        :param connection: the database connection
        :param cursor: the cursor for the database
        '''
        super(SessionInfoTable, self).__init__(connection, cursor)
        self.info = self.read_info()

    def read_info(self):
        '''
        :rtype: :class:`~kitty.data.data_manager.SessionInfo`
        :return: current session info
        '''
        self.select('*')
        row = self._cursor.fetchone()
        if not row:
            return None
        info_d = self.row_to_dict(row)
        return SessionInfo.from_dict(info_d)

    def set_session_info(self, info):
        '''
        :type info: :class:`~kitty.data.data_manager.SessionInfo`
        :param info: info to set
        '''
        if not self.info:
            self.info = SessionInfo()
            info_d = self.info.as_dict()
            ks = []
            vs = []
            for k, v in info_d.items():
                ks.append(k)
                vs.append(v)
            self.insert(ks, vs)
        changed = self.info.copy(info)
        if changed:
            self.update(self.info.as_dict())

    def get_session_info(self):
        '''
        :rtype: :class:`~kitty.data.data_manager.SessionInfo`
        :return: current session info
        '''
        if self.info:
            return SessionInfo(self.info)
        return None


class SessionInfo(object):
    '''
    session information manager
    '''

    fields = [i[0] for i in SessionInfoTable.__TABLE_FIELDS__]

    def __init__(self, orig=None):
        '''
        :param orig: SessionInfo object to copy (default: None)
        '''
        self.start_time = 0
        self.start_index = 0
        self.current_index = 0
        self.end_index = None
        self.failure_count = 0
        self.kitty_version = ''
        self.data_model_hash = 0
        self.test_list_str = ''
        if orig:
            self.copy(orig)

    def copy(self, orig):
        '''
        :param orig: SessionInfo object to copy
        :return: True if changed, false otherwise
        '''
        changed = False
        for attr in SessionInfo.fields:
            oattr = getattr(orig, attr)
            if getattr(self, attr) != oattr:
                setattr(self, attr, oattr)
                changed = True
        return changed

    def as_dict(self):
        '''
        :return: dictionary with the object fields
        '''
        return {fname: getattr(self, fname) for fname in SessionInfo.fields}

    @classmethod
    def from_dict(cls, info_d):
        '''
        :param info_d: the info dictionary
        :rtype: :class:`~kitty.data.data_manager.SessionInfo`
        :return: object that corresponds to the info dictionary
        '''
        info = SessionInfo()
        for k, v in info_d.items():
            setattr(info, k, v)
        return info
