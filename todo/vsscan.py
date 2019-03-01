'''
Scan USB host for vendor specific device support

Usage:
    umap2vsscan -P=PHY_INFO [-q] [-d=DB_FILE] [-s=VID:PID] [-t=TIMEOUT] [-z|-b=DELAY] [-r=RESUME_FILE] [-o=OS]  [-e] [-v ...]

Options:
    -P --phy PHY_INFO           physical layer info, see list below
    -v --verbose                verbosity level
    -q --quiet                  quiet mode. only print warning/error messages
    -d --db DB_FILE             vid, pid database file (see DB_FILE below)
    -s --vid_pid VID:PID        specific VID:PID combination scan
    -t --timeout TIMEOUT        seconds to wait for host to detect each device (defualt: 3)
    -r --resume RESUME_FILE     filename to store/load scan session data
    -z --single_step            wait for keypress between each test
    -b --between DELAY          delay in seconds to wait between tests
    -o --os OS                  specify the host OS (default: Linux)
    -e --exhaustive             go over each (vid, pid) combination - do not skip device if its driver is in the supported list

Physical layer:
    fd:<serial_port>        use facedancer connected to given serial port
    gadgetfs                use gadgetfs (requires mounting of gadgetfs beforehand)

DB_FILE:
    a python file with a db member which is a list of DBEntry() objects.
    a sample can be found at: umap2/data/vid_pid_db.py

OS:
    Linux, Windows, OSX, QNX

VID:PID
    can be of the form 1234:5678 or 1234-1236:1235-1555

Examples:
    scan using a db file with 5 seconds timeout and 2 seconds delay between tries
    $ umap2vsscan -P fd:/dev/ttyUSB0 -d vid_pid_db.py -t 5 -b 2
    scan using facedancer a specific vid:pid with 5 seconds timeout
    $ umap2vsscan -P fd:/dev/ttyUSB0 -s 2058:1005 -t 5
'''
import time
import traceback
import os
import signal
import sys
import six
from six.moves import cPickle
from umap2.apps.base import Umap2App
from umap2.dev.vendor_specific import USBVendorSpecificDevice


class OS(object):
    LINUX = 'Linux'
    WINDOWS = 'Windows'
    OSX = 'OSX'
    QNX = 'QNX'


class DBEntry(object):
    '''
    DBEnrty describes a vid, pid.
    '''

    def __init__(self, vid, pid, vendor_name='', product_name='', drivers={}, constraints=[], info={}):
        self.vid = vid
        self.pid = pid
        self.vendor_name = vendor_name
        self.product_name = product_name
        self.drivers = drivers
        self.constraints = constraints
        self.info = info
        self.os = None

    def __str__(self):
        s = 'vid:pid %04x:%04x' % (self.vid, self.pid)
        if self.vendor_name:
            s += ', vendor: %s' % self.vendor_name
        if self.product_name:
            s += ', product: %s' % self.product_name
        if self.drivers:
            if self.os and self.os in self.drivers:
                s += ', driver: %s' % self.drivers[self.os]
            else:
                s += ', drivers: %s' % self.drivers
        if self.constraints:
            s += ', constraints: %s' % self.constraints
        if self.info:
            s += ', info: %s' % self.info
        return s

    def vidpid(self):
        return '%04x:%04x' % (self.vid, self.pid)


class _ScanSession(object):

    def __init__(self):
        self.timeout = 5
        self.db = []
        self.supported = []
        self.unsupported = []
        self.supported_drivers = []
        # key: device that got no response
        # value: previous device (if any)
        self.no_response = {}
        self.current = 0


class Umap2VSScanApp(Umap2App):

    def __init__(self, options):
        super(Umap2VSScanApp, self).__init__(options)
        self.current_usb_function_supported = False
        self.scan_session = _ScanSession()
        self.start_time = 0
        self.stop_signal_received = False
        self.between_delay = 5
        signal.signal(signal.SIGINT, self.signal_handler)
        timeout = self.options['--timeout']
        if timeout:
            self.scan_session.timeout = int(timeout)
        self.single_step = False
        if self.options['--single_step']:
            self.single_step = True
        elif self.options['--between']:
            self.between_delay = int(self.options['--between'])
        self.os = self.options['--os']
        if not self.os:
            self.os = OS.LINUX
        else:
            if self.os not in [getattr(OS, x) for x in dir(OS) if not x.startswith('_')]:
                self.error('Unsupported OS: %s choose a supported OS or add the new one to the OS class' % self.os)

    def get_device_info(self, device):
        info = []
        if device.endpoints:
            for e in device.endpoints:
                info.append(device.endpoints[e].get_descriptor(valid=True))
        else:
            info = ''
        if info:
            return 'num_endpoints = %d' % len(info)
        else:
            return 'device not reached set configuration state'

    def load_db_from_file(self, db_file):
        self.logger.info('loading vid_pid db file: %s' % db_file)
        dirpath, filename = os.path.split(db_file)
        modulename = filename[:-3]
        if dirpath in sys.path:
            sys.path.remove(dirpath)
        sys.path.insert(0, dirpath)
        module = __import__(modulename, globals(), locals(), [], -1)
        self.scan_session.db = module.db
        self.logger.always('loaded %d entries' % len(self.scan_session.db))

    def build_db_from_vid_pid(self, vid_pid):
        vid, pid = vid_pid.split(':')
        if '-' in vid:
            vid_start = int(vid.split('-')[0], 16)
            vid_end = int(vid.split('-')[1], 16)
            self.logger.debug('vid start=%04x, vid_end=%04x' % (vid_start, vid_end))
            vid = six.moves.range(vid_start, vid_end)
        else:
            vid = [int(vid, 16)]
        if '-' in pid:
            pid_start = int(pid.split('-')[0], 16)
            pid_end = int(pid.split('-')[1], 16)
            self.logger.debug('pid start=%04x, pid_end=%x' % (pid_start, pid_end))
            pid = six.moves.range(pid_start, pid_end)
        else:
            pid = [int(pid, 16)]
        for v in vid:
            for p in pid:
                self.scan_session.db.append(DBEntry(v, p))

    def build_scan_session(self):
        self.resume_file = self.options['--resume']
        if self.resume_file and os.path.exists(self.resume_file):
                self.logger.always('Resume file found. Loading scan data')
                with open(self.resume_file, 'rb') as rf:
                    self.scan_session = cPickle.load(rf)
        else:
            db_file = self.options['--db']
            vid_pid = self.options['--vid_pid']
            self.logger.always('Resume file not found. Creating new one')
            if db_file and vid_pid:
                self.logger.warning('not expecting both db file and specific vid:pid. we will use vid:pid')
            if vid_pid:
                self.build_db_from_vid_pid(vid_pid)
            elif db_file:
                self.load_db_from_file(db_file)
            else:
                self.logger.error('Must select a scan option - db (-d) or specific vid:pid (-p)')
                return

    def sync_and_increment_session(self):
        self.scan_session.current += 1
        self.sync_session()

    def sync_session(self):
        if self.resume_file:
            with open(self.resume_file, 'wb') as rf:
                cPickle.dump(self.scan_session, rf, 2)

    def print_results(self):
        num_supported = len(self.scan_session.supported)
        # num_unsupported = len(self.scan_session.unsupported)
        self.logger.always('----------------------------------------')
        self.logger.always('Found %s supported device(s) (out of %s):' % (num_supported, self.scan_session.current))
        for i, db_entry in enumerate(self.scan_session.supported):
            self.logger.always('%d. %s' % (i, db_entry))
        self.logger.always('----------------------------------------')
        self.logger.always('Devices with no response (previous):')
        for i in sorted(self.scan_session.no_response.keys()):
            if self.scan_session.no_response[i]:
                prev = self.scan_session.no_response[i]
                pvp = self.scan_session.db[prev].vidpid()
            else:
                pvp = None
            self.logger.always('%s (%s)' % (self.scan_session.db[i], pvp))

    def run(self):
        self.build_scan_session()
        self.logger.always('Scanning host for supported vendor specific devices')
        phy = self.load_phy(self.options['--phy'])
        self.prev_index = None
        while self.scan_session.current < (len(self.scan_session.db)):
            if self.stop_signal_received:
                break
            db_entry = self.scan_session.db[self.scan_session.current]
            db_entry.os = self.os
            vid = db_entry.vid
            pid = db_entry.pid
            if not self.options['--exhaustive']:
                driver = db_entry.drivers.get(self.os, None)
                if driver and driver in self.scan_session.supported_drivers:
                    self.logger.always('skipping entry: %s' % db_entry)
                    self.sync_and_increment_session()
                    continue
            self.logger.always('Testing support for %s' % db_entry)
            self.setup_packet_received = False
            self.current_usb_function_supported = False
            self.start_time = time.time()
            device = USBVendorSpecificDevice(self, phy, vid, pid)
            try:
                device.connect()
                device.run()
            except:
                self.logger.error(traceback.format_exc())
            device.disconnect()
            if not self.is_host_alive():
                break
            if self.current_usb_function_supported:
                db_entry.info = self.get_device_info(device)
                self.scan_session.supported.append(db_entry)
                driver = db_entry.drivers.get(self.os, None)
                if driver:
                    self.scan_session.supported_drivers.append(db_entry.drivers[self.os])
            # else:
            #     db_entry.info = self.get_device_info(device)
            #     self.scan_session.unsupported.append(db_entry)
            self.prev_index = self.scan_session.current
            self.sync_and_increment_session()
            if self.single_step:
                raw_input('press any key to continue')
            else:
                time.sleep(self.between_delay)
        self.print_results()

    def is_host_alive(self):
        if not self.setup_packet_received:
            self.logger.error('Host appears to have died or is simply ignoring us :(')
            current_index = self.scan_session.current
            if current_index not in self.scan_session.no_response:
                self.scan_session.no_response[current_index] = self.prev_index
            self.sync_session()
        return self.setup_packet_received

    def usb_function_supported(self, reason=None):
        '''
        Callback from a USB device, notifying that the current USB device
        is supported by the host.

        :param reason: reason why we decided it is supported (default: None)
        '''
        self.current_usb_function_supported = True

    def signal_handler(self, signal, frame):
        self.stop_signal_received = True

    def should_stop_phy(self):
        stop_phy = False
        time_elapsed = int(time.time() - self.start_time)
        if self.current_usb_function_supported:
            stop_phy = True
        elif time_elapsed >= self.scan_session.timeout:
            self.logger.info('have been waiting long enough (over %d secs.), disconnect' % (time_elapsed))
            stop_phy = True
        return stop_phy


def main():
    app = Umap2VSScanApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()

