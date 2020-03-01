#
# This file is part of FaceDancer.
#
""" Functionality for declaring and working with USB control requests. """


import inspect
import logging
import warnings
import functools
#import construct

from enum import IntEnum
from abc import ABCMeta, abstractmethod

from .types import USBDirection, USBRequestRecipient, USBRequestType

logger = logging.getLogger(__name__)

def _wrap_with_field_matcher(func, field_name, field_value):
    """ Internal function that generates a request-refinement decorator.

    TODO: better doctstring
    """

    @functools.wraps(func)
    def _wrapped(caller, request):
        if getattr(request, field_name) == field_value:
            func(caller, request)
        else:
            raise NotImplementedError()

    return _wrapped


class ControlRequestHandler:
    """ Class representing a control request handler.

    Instances of this class are generated automatically each time a control request is
    defined using decorator syntax; and track the association between the relevant handler
    function and the condition under which it's executed.
    """

    def __init__(self, handler_function, execution_condition):
        self._handler   = handler_function
        self._condition = execution_condition


    def __call__(self, caller, request):
        if self._condition(request):
            try:
                self._handler(caller, request)
                return True
            except NotImplementedError:
                return False


    def add_condition(self, condition):
        """ Refines a control request handler such that it's only called when the added condition is true. """
        base_condition = self._condition
        self._condition = lambda req : base_condition(req) and condition(req)


    def add_field_matcher(self, field_name, field_value):
        """ Refines a control request handler such that it's only called when one of its fields matches a given value.

        Parameters:
            field_name -- The property of the USBControlRequest object to be checked.
            field_value -- The value the relevant property must match to be called.
        """
        matcher = lambda req : getattr(req, field_name) == field_value
        self.add_condition(matcher)


    def __repr__(self):
        return f"<ControlRequestHandler wrapping {self._handler.__qualname__} at 0x{id(self):x}"



def control_request_handler(condition=lambda _ : True, **kwargs):
    """ Decorator that declares a control request handler.

    Used while defining a USBDevice, USBInterface, USBEndpoint, or
    USBOtherRecipient class to declare handlers for that function.

    Parameters:
        condition -- A function that, when evaluated on a USBControlRequest, evaluates
                     true if and only if this function is an appropriate handler.
    """

    def decorator(func):

        # Wrap the handler function with a ControlRequestHandler, which will handle
        # conditional execution of the relevant function.
        handler = ControlRequestHandler(func, condition)

        # Treat any keyword arguments passed to us beyond our condition as field matchers;
        # which specify the properties a given request must have to trigger this handler.
        for field, value in kwargs.items():
            handler.add_field_matcher(field, value)

        return handler

    return decorator


def standard_request_handler(**kwargs):
    """ Decorator; declares a standard request handler. See control_request_handler() for usage. """
    return control_request_handler(type=USBRequestType.STANDARD, **kwargs)


def vendor_request_handler(**kwargs):
    """ Decorator; declares a vendor request handler. See control_request_handler() for usage. """
    return control_request_handler(type=USBRequestType.VENDOR, **kwargs)


def class_request_handler(**kwargs):
    """ Decorator; declares a class request handler. See control_request_handler() for usage. """
    return control_request_handler(type=USBRequestType.CLASS, **kwargs)


def reserved_request_handler(**kwargs):
    """ Decorator; declares a reserved-type request handler. Not typically used. """
    return control_request_handler(type=USBRequestType.RESERVED, **kwargs)


#
# Convenience request-refining decorators.
#

def to_device(func):
    """ Decorator; refines a handler so it's only called on requests with a device recipient. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.DEVICE)


# FIXME: should this implicitly be "to_this_endpoint" and "to_any_endpoint"?
def to_endpoint(func):
    """ Decorator; refines a handler so it's only called on requests with an endpoint recipient. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.ENDPOINT)


# FIXME: should this implicitly be "to_this_interface" and "to_any_interface"?
def to_interface(func):
    """ Decorator; refines a handler so it's only called on requests with an interface recipient. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.INTERFACE)


def to_other(func):
    """ Decorator; refines a handler so it's only called on requests with an Other (TM) recipient. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.OTHER)




def get_request_handler_methods(cls):
    members = inspect.getmembers(cls)
    return [m for _, m in members if isinstance(m, ControlRequestHandler)]



class USBControlRequest:
    """ Class encapsulating a USB control request. """

    _type_descriptions = {
        0:  'standard',
        1:  'class',
        2:  'vendor',
        3:  'INVALID',
    }

    _recipent_descriptions = {
        0: 'device',
        1: 'interface',
        2: 'endpoint',
        3: 'other',
    }

    # TODO: split me up by recipient
    _standard_req_descriptions = {
        0: 'GET_STATUS',
        1: 'CLEAR_FEATURE',
        3: 'SET_FEATURE',
        5: 'SET_ADDRESS',
        6: 'GET_DESCRIPTOR',
        7: 'SET_DESCRIPTOR',
        8: 'GET_CONFIGRUATION',
        9: 'SET_CONFIGURATION',
        10: 'GET_INTERFACE',
        11: 'SET_INTERFACE',
        12: 'SYNCH_FRAME'
    }

    _descriptor_number_description = {
        1: 'DEVICE',
        2: 'CONFIGURATION',
        3: 'STRING',
        4: 'INTERFACE',
        5: 'ENDPOINT',
        6: 'DEVICE_QUALIFIER',
        7: 'OTHER_SPEED_CONFIG',
        8: 'POWER',
        33: 'HID',
        34: 'REPORT',
    }

    def __init__(self, raw_bytes):
        """Expects raw 8-byte setup data request packet"""

        self.request_type   = raw_bytes[0]
        self.number         = raw_bytes[1]
        self.value          = (raw_bytes[3] << 8) | raw_bytes[2]
        self.index          = (raw_bytes[5] << 8) | raw_bytes[4]
        self.length         = (raw_bytes[7] << 8) | raw_bytes[6]
        self.data           = raw_bytes[8:]



    @property
    def request(self):
        warnings.warn('`request` should be replaced with `number`', DeprecationWarning)
        return self.number


    @property
    def recipient(self):
        return self.get_recipient()


    @property
    def type(self):
        return self.get_type()


    def __str__(self):
        s = "dir=%d, type=%x, rec=%x, r=%x, v=%x, i=%x, l=%d" \
                % (self.get_direction(), self.get_type(), self.get_recipient(),
                   self.number, self.value, self.index, self.length)
        return s


    def __repr__(self):
        direction_marker = "<" if self.get_direction() == 1 else ">"

        # Pretty print, where possible.
        type = self.get_type_string()
        recipient = self.get_recipient_string()
        request = self.get_request_number_string()
        value = self.get_value_string()

        s = "%s, %s request to %s (%s: value=%s, index=%x, length=%d)" \
                % (direction_marker, type, recipient, request,
                   value, self.index, self.length)
        return s


    def get_type_string(self):
        return self._type_descriptions[self.get_type()]

    def get_recipient_string(self):
        return self._recipent_descriptions[self.get_recipient()]

    def get_request_number_string(self):
        if self.get_type() == 0:
            return self._get_standard_request_number_string()
        else:
            type = self.get_type_string()
            return "{} request {}".format(type, self.request)

    def _get_standard_request_number_string(self):
        if self.request in self._standard_req_descriptions:
            return self._standard_req_descriptions[self.request]
        else:
            return "unknown request {}".format(self.request)

    def get_value_string(self):
        # If this is a GET_DESCRIPTOR request, parse it.
        if self.get_type() == 0 and self.request == 6:
            descriptor_index = self.value & 0xff
            description = self.get_descriptor_number_string()
            return "{} descriptor (index=0x{:02x})".format(description, descriptor_index)
        else:
            return "%x" % self.value

    def get_descriptor_number_string(self):
        try:
            descriptor_index = self.value >> 8
            return self._descriptor_number_description[descriptor_index]
        except KeyError:
            return "unknown descriptor 0x%x" % self.value

    def raw(self):
        """returns request as bytes"""
        b = bytes([ self.request_type, self.request,
                    self.value  & 0xff, (self.value  >> 8) & 0xff,
                    self.index  & 0xff, (self.index  >> 8) & 0xff,
                    self.length & 0xff, (self.length >> 8) & 0xff
                  ])
        return b

    def get_direction(self):
        return (self.request_type >> 7) & 0x01

    def get_type(self):
        return (self.request_type >> 5) & 0x03

    def get_recipient(self):
        return self.request_type & 0x1f

    # meaning of bits in wIndex changes whether we're talking about an
    # interface or an endpoint (see USB 2.0 spec section 9.3.4)
    def get_index(self):
        rec = self.get_recipient()
        if rec == 1:                # interface
            return self.index
        elif rec == 2:              # endpoint
            return self.index & 0x0f


class USBRequestHandler(metaclass=ABCMeta):
    """ Base class for any object that handles USB requests. """


    @abstractmethod
    def _request_handlers(self):
        """ Returns an iterable of request handlers provided by the class. """


    def _get_subordinate_handlers(self):
        """ Returns a list of subordinate handlers who should have an opportunity to handle requests.

        Normally called by _call_subordinate_handlers; may not be valid if that function is overridden.
        """
        return ()


    def _call_subordinate_handlers(self, request):
        """ Calls the ``handle_request`` method of any subordinate handlers.

        This default implementation uses get_subordinates to get an iterable
        of subordiantes we should call handle_request on.
        """

        handled = False

        for configuration in self._get_subordinate_handlers():
            handled = handled or configuration.handle_request(request)

        return handled



    def handle_request(self, request):
        """ Core control request handler.

        This function can be overridden by a subclass if desired; but the typical way to
        handle a specific control request is to the the ``@control_request_handler`` decorators.

        Parameters:
            request -- the USBControlRequest object representing the relevant request
        """

        handled = False

        # Our default implementation is simple: we try every handler; allowing any
        # handler that wants to handle the relevant function a chance to handle it.
        #
        # Calling the handler for _every_ matching request (as opposed to e.g. the first one)
        # allows one to trivially add observers.
        for handler in self._request_handlers():
            handled = handled or handler(self, request)

        # Pass our requests down to our subordinates, as well.
        handled = handled or self._call_subordinate_handlers(request)
        return handled
