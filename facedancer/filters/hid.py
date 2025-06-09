#
# USBProxy HID logging
#

from warnings import filterwarnings
import hid_parser
from hid_parser import HIDComplianceWarning
from enum import IntEnum

from facedancer.descriptor import USBDescriptorTypeNumber
from facedancer.device import USBBaseDevice
from facedancer.filters.base import USBProxyFilter
from facedancer.request import USBControlRequest
from facedancer.types import (
    USBDirection,
    USBRequestRecipient,
    USBRequestType,
    USBStandardRequests,
)

from ..logging import log

GET_REPORT = 0x01
SET_REPORT = 0x09

SET_IDLE = 0x0A

filterwarnings("ignore", r"Usage.* has no compatible usage types", HIDComplianceWarning)
filterwarnings("ignore", r"Expecting 60 usages but got 1", HIDComplianceWarning)


class HIDReportType(IntEnum):
    HID_TYPE_INPUT = 1
    HID_TYPE_OUTPUT = 2
    HID_TYPE_FEATURE = 3


class USBProxyHIDFilter(USBProxyFilter):
    """
    Print HID packets

    If verbose > 2 - print all fields
    """

    def __init__(self, device: USBBaseDevice, verbose=1):
        self.device = device
        self.verbose = verbose
        self.rdescs = {}

    def filter_control_in(self, req: USBControlRequest | None, data, stalled):
        if req:
            if req.type == USBRequestType.STANDARD and USBRequestRecipient.INTERFACE:
                if req.number == USBStandardRequests.GET_DESCRIPTOR:
                    self._log_desc(req, data)

            if req.type == USBRequestType.CLASS and USBRequestRecipient.INTERFACE:
                self._log_in(req, data)

        return req, data, stalled

    def _log_desc(self, req, data):
        kind = req.value_high
        iface = req.index
        # index = req.value_low

        if kind == USBDescriptorTypeNumber.HID:
            log.info(f"GET_DESC HID_DEVICE I{iface} {dump(data)}")

        if kind == USBDescriptorTypeNumber.REPORT:
            log.info(f"GET_DESC HID_REPORT I{iface} {dump(data)}")
            try:
                self.rdescs[iface] = rdesc = hid_parser.ReportDescriptor(data)
            except NotImplementedError as e:
                log.warning(f"Failed to parse report: {e}")
                self.rdescs[iface] = None
                return

            if self.verbose > 2:
                for rid in rdesc.output_report_ids:
                    log.info(f"  output {rid} {rdesc.get_output_report_size(rid)}")

                for rid in rdesc.input_report_ids:
                    log.info(f"  input {rid} {rdesc.get_input_report_size(rid)}")

                for rid in rdesc.feature_report_ids:
                    log.info(f"  feature {rid} {rdesc.get_feature_report_size(rid)}")

    def _log_in(self, req, data):
        iface = req.index

        if req.number == GET_REPORT:
            kind = HIDReportType(req.value_high)
            log.info(f"GET_REPORT {kind} RID {req.value_low} I{iface} {dump(data)}")

            self._report(iface, "parse_input_report", data)

    def filter_control_out(self, req, data):
        if req and req.type == USBRequestType.CLASS and USBRequestRecipient.INTERFACE:
            self._log_out(req, data)

        return req, data

    def _log_out(self, req, data):
        iface = req.index

        if req.number == SET_REPORT:
            kind = HIDReportType(req.value_high)
            log.info(f"SET_REPORT {kind} RID {req.value_low} I{iface} {dump(data)}")
            self._report(iface, "parse_output_report", data)

        if req.number == SET_IDLE:
            dur = req.value_high * 4
            log.info(f"SET_IDLE {dur}ms RID {req.value_low} I{iface} {dump(data)}")

    def filter_in(self, ep_num, data):
        if interface := self._find_interface(ep_num):
            self._log_ep_in(interface.number, ep_num, data)

        return ep_num, data

    def _find_interface(self, ep_num):
        """Return the interface that has ep_num."""
        if not self.device.configuration:
            return

        for interface in self.device.configuration.active_interfaces.values():
            if interface.has_endpoint(ep_num, USBDirection.IN):
                return interface

    def _log_ep_in(self, iface, num, data):
        log.info(f"EP{num} I{iface} RID {data[0]} {dump(data[1:])}")
        self._report(iface, "parse_input_report", data)

    def _report(self, iface: int, kind: str, data: bytes):
        if self.verbose < 3:
            return

        rdesc = self.rdescs.get(iface)
        if len(data) > 1 and rdesc:
            try:
                # TODO - handle feature
                for usage, value in getattr(rdesc, kind)(data).items():
                    log.info(f"  {usage} {value}")
            except Exception as e:
                log.warning(f"  {e}")


def dump(raw: bytes):
    return raw.hex(" ", -2)
