'''
.. todo::

    Something to check all over the place - little/big endianess of data
    It is better now (6/6/2016) but still needs improvements

.. todo::

    it seems that our current phy, facedancer, is very slow,
    so we are only able to emulate very small disk images (~3M).
    Take that into consideration before using it ...
'''
from mmap import mmap
import os
import struct
from binascii import hexlify
from threading import Thread, Event
import time

from six.moves.queue import Queue
from facedancer.usb.USBDevice import USBDevice
from facedancer.usb.USBConfiguration import USBConfiguration
from facedancer.usb.USBInterface import USBInterface
from facedancer.usb.USBEndpoint import USBEndpoint
from facedancer.usb.USBClass import USBClass
from facedancer.usb.USB import USBDescribable
from facedancer.fuzz.helpers import mutable


class ScsiCmds(object):
    TEST_UNIT_READY = 0x00
    REQUEST_SENSE = 0x03
    READ_6 = 0x08
    WRITE_6 = 0x0A
    INQUIRY = 0x12
    MODE_SENSE_6 = 0x1A
    SEND_DIAGNOSTIC = 0x1D
    PREVENT_ALLOW_MEDIUM_REMOVAL = 0x1E
    READ_FORMAT_CAPACITIES = 0x23
    READ_CAPACITY_10 = 0x25
    READ_10 = 0x28
    WRITE_10 = 0x2A
    VERIFY_10 = 0x2F
    SYNCHRONIZE_CACHE = 0x35
    MODE_SENSE_10 = 0x5A
    READ_CAPACITY_16 = 0x9e


class ScsiSenseKeys(object):
    GOOD = 0x00
    RECOVERED_ERROR = 0x01
    NOT_READY = 0x02
    MEDIUM_ERROR = 0x03
    HARDWARE_ERROR = 0x04
    ILLEGAL_REQUEST = 0x05
    UNIT_ATTENTION = 0x06
    DATA_PROTECT = 0x07
    BLANK_CHECK = 0x08
    VENDOR_SPECIFIC = 0x09
    COPY_ABORTED = 0x0A
    ABORTED_COMMAND = 0x0B
    VOLUME_OVERFLOW = 0x0D
    MISCOMPARE = 0x0E


class ScsiCmdStatus(object):
    COMMAND_PASSED = 0x00
    COMMAND_FAILED = 0x01
    PHASE_ERROR = 0x02


class USBMassStorageClass(USBClass):
    name = 'MassStorageClass'

    def __init__(self, phy, scsi_device):
        super(USBMassStorageClass, self).__init__(phy)
        self.scsi_device = scsi_device

    def setup_local_handlers(self):
        self.local_handlers = {
            0xFF: self.handle_bulk_only_mass_storage_reset,
            0xFE: self.handle_get_max_lun,
        }

    @mutable('msc_bulk_only_mass_storage_reset_response')
    def handle_bulk_only_mass_storage_reset(self, req):
        self.scsi_device.handle_reset()
        return b''

    @mutable('msc_get_max_lun_response')
    def handle_get_max_lun(self, req):
        return b'\x00'


class DiskImage:
    def __init__(self, filename, block_size):
        self.filename = filename
        self.block_size = block_size

        try:
            statinfo = os.stat(self.filename)
            self.size = statinfo.st_size
            self.file = open(self.filename, 'r+b')
            self.image = mmap(self.file.fileno(), 0)
        except:
            print('''
----------------------------------------------------------------------
No disk image named '%s' was found.
You can use the disk image from facedancer/examples/fat32.3M.stick.img
as a small disk image (extract it using `tar xvf fat32.3M.stick.img`)
----------------------------------------------------------------------
            ''' % (filename))
            raise Exception('No file named %s found.' % (filename))

    def close(self):
        self.image.flush()
        self.image.close()

    def get_sector_count(self):
        return (self.size // self.block_size) - 1

    def get_sector_data(self, address):
        block_start = address * self.block_size
        block_end = block_start + self.block_size   # slices are NON-inclusive
        return self.image[block_start:block_end]

    def put_sector_data(self, address, data):
        block_start = address * self.block_size
        block_end = (address + 1) * self.block_size   # slices are NON-inclusive

        pad_len = (self.block_size - (len(data) % self.block_size)) % self.block_size
        data += '\x00' * pad_len
        self.image[block_start:block_end] = data[:self.block_size]
        self.image.flush()


def scsi_status(cbw, status):
    csw = b'USBS' + cbw.tag + struct.pack('<IB', 0x00000000, status)
    return csw


class ScsiDevice(USBDescribable):
    '''
    Implementation of subset of the SCSI protocol
    '''
    name = 'ScsiDevice'

    def __init__(self, phy, disk_image):
        super(ScsiDevice, self).__init__(phy)
        self.disk_image = disk_image
        self.handlers = {
            ScsiCmds.INQUIRY: self.handle_inquiry,
            ScsiCmds.REQUEST_SENSE: self.handle_request_sense,
            ScsiCmds.TEST_UNIT_READY: self.handle_test_unit_ready,
            ScsiCmds.READ_CAPACITY_10: self.handle_read_capacity_10,
            # ScsiCmds.SEND_DIAGNOSTIC: self.handle_send_diagnostic,
            ScsiCmds.PREVENT_ALLOW_MEDIUM_REMOVAL: self.handle_prevent_allow_medium_removal,
            ScsiCmds.WRITE_10: self.handle_write_10,
            ScsiCmds.READ_10: self.handle_read_10,
            # ScsiCmds.WRITE_6: self.handle_write_6,
            # ScsiCmds.READ_6: self.handle_read_6,
            # ScsiCmds.VERIFY_10: self.handle_verify_10,
            ScsiCmds.MODE_SENSE_6: self.handle_mode_sense_6,
            ScsiCmds.MODE_SENSE_10: self.handle_mode_sense_10,
            ScsiCmds.READ_FORMAT_CAPACITIES: self.handle_read_format_capacities,
            ScsiCmds.SYNCHRONIZE_CACHE: self.handle_synchronize_cache,
            ScsiCmds.READ_CAPACITY_16: self.handle_read_capacity_16,
        }
        self.is_write_in_progress = False
        self.handle_reset()
        self.stop_event = Event()
        self.thread = Thread(target=self.handle_data_loop)
        self.thread.daemon = True
        self.thread.start()

    def handle_reset(self):
        self.debug('handling reset')
        if self.is_write_in_progress and self.write_data:
            self.disk_image.put_sector_data(self.write_base_lba, self.write_data)
        self.is_write_in_progress = False
        self.write_cbw = None
        self.write_base_lba = 0
        self.write_length = 0
        self.write_data = b''
        self.tx = Queue()
        self.rx = Queue()

    def stop(self):
        self.stop_event.set()

    def handle_data_loop(self):
        while not self.stop_event.isSet():
            if not self.rx.empty():
                data = self.rx.get()
                self.handle_data(data)
            else:
                time.sleep(0.0001)

    def handle_data(self, data):
        if self.is_write_in_progress:
            self.handle_write_data(data)
        else:
            cbw = CommandBlockWrapper(data)
            opcode = cbw.opcode
            if opcode in self.handlers:
                try:
                    resp = self.handlers[opcode](cbw)
                    if resp is not None:
                        self.tx.put(resp)
                    self.tx.put(scsi_status(cbw, ScsiCmdStatus.COMMAND_PASSED))
                except Exception as ex:
                    self.warning('exception while processing opcode %#x' % (opcode))
                    self.warning(ex)
                    self.tx.put(scsi_status(cbw, ScsiCmdStatus.COMMAND_FAILED))
            else:
                self.error('No handler for opcode %#x, return CSW with ScsiCmdStatus.COMMAND_FAILED' % (opcode))
                self.tx.put(scsi_status(cbw, ScsiCmdStatus.COMMAND_FAILED))

    def handle_write_data(self, data):
        self.write_data += data
        self.debug('Got %#x bytes of SCSI write data, written so far: %#x' % (len(data), len(self.write_data)))
        if len(self.write_data) >= self.write_length:
            self.info('Got all write data')
            # done writing
            self.disk_image.put_sector_data(self.write_base_lba, self.write_data)
            self.is_write_in_progress = False
            self.write_data = b''
            self.tx.put(scsi_status(self.write_cbw, ScsiCmdStatus.COMMAND_PASSED))

    @mutable('scsi_inquiry_response')
    def handle_inquiry(self, cbw):
        self.debug('SCSI Inquiry, data: %s' % hexlify(cbw.cb[1:]))
        peripheral = 0x00  # SBC
        RMB = 0x80  # Removable
        version = 0x00
        response_data_format = 0x01
        config = (0x00, 0x00, 0x00)
        vendor_id = b'MBYDCOR '
        product_id = b'FD DISK IMAGE '
        product_revision_level = b'8.02'
        part1 = struct.pack('BBBB', peripheral, RMB, version, response_data_format)
        part2 = struct.pack('BBB', *config) + vendor_id + product_id + product_revision_level
        length = struct.pack('B', len(part2))
        response = part1 + length + part2
        return response

    @mutable('scsi_request_sense_response')
    def handle_request_sense(self, cbw):
        self.debug('SCSI Request Sense, data: %s' % hexlify(cbw.cb[1:]))
        response_code = 0x70
        valid = 0x00
        filemark = 0x06
        information = 0x00000000
        command_info = 0x00000000
        additional_sense_code = 0x3a
        additional_sens_code_qualifier = 0x00
        field_replacement_unti_code = 0x00
        sense_key_specific = b'\x00\x00\x00'

        part1 = struct.pack('<BBBI', response_code, valid, filemark, information)
        part2 = struct.pack(
            '<IBBB',
            command_info,
            additional_sense_code,
            additional_sens_code_qualifier,
            field_replacement_unti_code
        )
        part2 += sense_key_specific
        length = struct.pack('B', len(part2))
        response = part1 + length + part2
        return response

    @mutable('scsi_test_unit_ready_response')
    def handle_test_unit_ready(self, cbw):
        self.debug('SCSI Test Unit Ready, logical unit number: %02x' % (cbw.cb[1]))

    @mutable('scsi_read_capacity_10_response')
    def handle_read_capacity_10(self, cbw):
        # .. todo: is the length correct?
        self.debug('SCSI Read Capacity(10), data: %s' % hexlify(cbw.cb[1:]))
        lastlba = self.disk_image.get_sector_count()
        length = self.disk_image.block_size
        response = struct.pack('>II', lastlba, length)
        return response

    @mutable('scsi_read_capacity_16_response')
    def handle_read_capacity_16(self, cbw):
        # .. todo: is the length correct?
        self.debug('SCSI Read Capacity(16), data: %s' % hexlify(cbw.cb[1:]))
        lastlba = self.disk_image.get_sector_count()
        length = self.disk_image.block_size
        response = struct.pack('>BBQIBB', 0x9e, 0x10, lastlba, length, 0x00, 0x00)
        return response

    @mutable('scsi_send_diagnostic_response')
    def handle_send_diagnostic(self, cbw):
        raise NotImplementedError('yet...')

    @mutable('scsi_prevent_allow_medium_removal_response')
    def handle_prevent_allow_medium_removal(self, cbw):
        self.debug('SCSI Prevent/Allow Removal')

    @mutable('scsi_write_10_response')
    def handle_write_10(self, cbw):
        self.debug('SCSI Write (10), data: %s' % hexlify(cbw.cb[1:]))

        base_lba = struct.unpack('>I', cbw.cb[2:6])[0]
        num_blocks = struct.unpack('>H', cbw.cb[7:9])[0]

        self.debug('SCSI Write (10), lba %#x + %#x block(s)' % (base_lba, num_blocks))

        # save for later
        self.write_cbw = cbw
        self.write_base_lba = base_lba
        self.write_length = num_blocks * self.disk_image.block_size
        self.debug('SCSI Write (10) total expected length: %#x' % (self.write_length))
        self.is_write_in_progress = True

    def handle_read_10(self, cbw):
        base_lba, group, num_blocks = struct.unpack('>IBH', cbw.cb[2:9])
        self.debug('SCSI Read (10), lba %#x + %#x block(s)' % (base_lba, num_blocks))
        for block_num in range(num_blocks):
            data = self.disk_image.get_sector_data(base_lba + block_num)
            self.tx.put(data)

    @mutable('scsi_write_6_response')
    def handle_write_6(self, cbw):
        raise NotImplementedError('yet...')

    @mutable('scsi_read_6_response')
    def handle_read_6(self, cbw):
        raise NotImplementedError('yet...')

    @mutable('scsi_verify_10_response')
    def handle_verify_10(self, cbw):
        raise NotImplementedError('yet...')

    def _build_page0_report(self, page, data):
        report = struct.pack('BB', page, len(data))
        report += data
        return report

    def _build_subpage_report(self, page, subpage, data):
        report = struct.pack('>BBH', page | 0x40, subpage, len(data))
        report += data
        return report

    def _report_header(self, mode_type, mode_data_length):
        # Based on seagate 100293068h.pdf
        medium_type = 0x00
        flags = 0x00
        block_descriptor_len = 0x00
        if mode_type == 6:  # Table 292
            header_data = struct.pack('>3B', medium_type, flags, block_descriptor_len)
            total_len = struct.pack('B', len(header_data) + mode_data_length)
        else:  # Table 293
            longlba = 0x00
            header_data = struct.pack('>BBBBH', medium_type, flags, longlba, 0, block_descriptor_len)
            total_len = struct.pack('>H', len(header_data) + mode_data_length)
        return total_len + header_data

    def _build_page_report(self, page, subpage, data):
        if subpage is None:
            report = self._build_page0_report(page, data)
        else:
            report = self._build_subpage_report(page, subpage, data)
        return report

    def handle_scsi_mode_sense(self, mode_type, page, subpage, alloc_len, ctrl, with_header=True):
        # .. todo: implement response for unsupported pages
        self.debug('SCSI Mode Sense(%d), page %#x subpage %#x' % (mode_type, page, subpage))
        report = None
        # wish there was a switch :(
        if page == 0x1c:
            # case: informational exceptions control (table 314)
            if subpage == 0x00:
                data = struct.pack('>BBII', 0x00, 0x05, 0x00, 0x00)
                report = self._build_page_report(page, 0x00, data)
            # case: background control (table 300)
            elif subpage == 0x01:
                data = struct.pack('>BBHHHHH', 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
                report = self._build_page_report(page, subpage, data)
            elif subpage == 0xff:
                report = self.handle_scsi_mode_sense(mode_type, 0x1c, 0x00, alloc_len, ctrl, False)
                report += self.handle_scsi_mode_sense(mode_type, 0x1c, 0x01, alloc_len, ctrl, False)
        # case: all pages
        elif page == 0x3f:
            # return all pages that we got ...
            report = self.handle_scsi_mode_sense(mode_type, 0x1c, 0xff, alloc_len, ctrl, False)
        if report is None:
            # default behaviour, taken from previous implementation
            # this should probably be changed ...
            report = '\x07\x00\x00\x00\x00\x00\x00\x00'
        if with_header:
            self.debug('SCSI mode sense (%d) - adding header' % (mode_type))
            report = self._report_header(mode_type, len(report)) + report
        return report

    @mutable('scsi_mode_sense_6_response')
    def handle_mode_sense_6(self, cbw):
        # .. todo: DBD, PC
        page, subpage, alloc_len, control = struct.unpack('>4B', cbw.cb[2:6])
        page &= 0x3f
        return self.handle_scsi_mode_sense(6, page, subpage, alloc_len, control)

    @mutable('scsi_mode_sense_10_response')
    def handle_mode_sense_10(self, cbw):
        # .. todo: LLBA, DBD, PC
        page, subpage, _, _, _, alloc_len, control = struct.unpack('>5BHB', cbw.cb[2:10])
        page &= 0x3f
        return self.handle_scsi_mode_sense(10, page, subpage, alloc_len, control)

    @mutable('scsi_read_format_capacities')
    def handle_read_format_capacities(self, cbw):
        self.debug('SCSI Read Format Capacity')
        # header
        response = struct.pack('>I', 8)
        num_sectors = 0x1000
        reserved = 0x1000
        sector_size = self.disk_image.block_size
        response += struct.pack('>IHH', num_sectors, reserved, sector_size)
        return response

    @mutable('scsi_synchronize_cache_response')
    def handle_synchronize_cache(self, cbw):
        self.debug('Synchronize Cache (10)')


class CommandBlockWrapper:
    def __init__(self, bytestring):
        as_array = bytearray(bytestring)
        self.signature = bytestring[0:4]
        self.tag = bytestring[4:8]
        self.data_transfer_length = struct.unpack('<I', bytestring[8:12])[0]
        self.flags = as_array[12]
        self.lun = as_array[13] & 0x0f
        self.cb_length = as_array[14] & 0x1f
        # self.cb = bytestring[15:15+self.cb_length]
        self.cb = as_array[15:]
        self.opcode = self.cb[0]

    def __str__(self):
        s = 'sig: %s\n' % hexlify(self.signature)
        s += 'tag: %s\n' % hexlify(self.tag)
        s += 'data transfer len: %s\n' % self.data_transfer_length
        s += 'flags: %s\n' % self.flags
        s += 'lun: %s\n' % self.lun
        s += 'command block len: %s\n' % self.cb_length
        s += 'command block: %s\n' % hexlify(self.cb)
        return s


class USBMassStorageInterface(USBInterface):
    '''
    .. todo:: all handlers - should be more dynamic??
    '''
    name = 'MassStorageInterface'

    def __init__(self, phy, scsi_device, usbclass, sub, proto):
        super(USBMassStorageInterface, self).__init__(
            phy=phy,
            interface_number=0,
            interface_alternate=0,
            interface_class=usbclass,
            interface_subclass=sub,
            interface_protocol=proto,
            interface_string_index=0,
            endpoints=[
                USBEndpoint(
                    phy=phy,
                    number=1,
                    direction=USBEndpoint.direction_out,
                    transfer_type=USBEndpoint.transfer_type_bulk,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=0x40,
                    interval=0,
                    handler=self.handle_data_available
                ),
                USBEndpoint(
                    phy=phy,
                    number=3,
                    direction=USBEndpoint.direction_in,
                    transfer_type=USBEndpoint.transfer_type_bulk,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=0x40,
                    interval=0,
                    handler=self.handle_buffer_available
                ),
            ],
            usb_class=USBMassStorageClass(phy, scsi_device),
        )
        self.scsi_device = scsi_device

    def handle_buffer_available(self):
        if not self.scsi_device.tx.empty():
            data = self.scsi_device.tx.get()
            self.send_on_endpoint(3, data)

    def handle_data_available(self, data):
        self.debug('handling %d bytes of SCSI data' % (len(data)))
        self.scsi_device.rx.put(data)


class USBMassStorageDevice(USBDevice):
    name = 'MassStorageDevice'

    def __init__(self, phy, vid=0x154b, pid=0x6545, rev=0x0002, \
        usbclass=USBClass.MassStorage, subclass=0x06, proto=0x50, \
        disk_image_filename='stick.img'
    ):
        self.disk_image = DiskImage(disk_image_filename, 0x200)
        self.scsi_device = ScsiDevice(phy,self.disk_image)

        super(USBMassStorageDevice, self).__init__(
            phy=phy,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='PNY',
            product_string='USB 2.0 FD',
            serial_number_string='4731020ef1914da9',
            configurations=[
                USBConfiguration(
                    phy=phy,
                    configuration_index=1,
                    configuration_string_or_index='MassStorage config',
                    interfaces=[
                        USBMassStorageInterface(phy, self.scsi_device, usbclass, subclass, proto)
                    ]
                )
            ],
        )

    def disconnect(self):
        super(USBMassStorageDevice, self).disconnect()
        self.scsi_device.stop()
        self.disk_image.close()

    def handle_set_address_request(self, req):
        '''
        When a new address is set,
        we should reset some flags in the scsi device ...
        '''
        self.scsi_device.handle_reset()
        super(USBMassStorageDevice, self).handle_set_address_request(req)

usb_device = USBMassStorageDevice
