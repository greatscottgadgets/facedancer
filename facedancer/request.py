#
# This file is part of Facedancer.
#
""" Functionality for declaring and working with USB control requests. """

import inspect
import warnings
import functools

from typing      import List, Iterable
from dataclasses import dataclass
from abc         import ABCMeta, abstractmethod

from .descriptor import USBDescribable
from .types      import USBRequestRecipient, USBRequestType, USBDirection, USBStandardRequests


def _wrap_with_field_matcher(func, field_name, field_value, match_index=False):
    """ Internal function; generates a request-refinement decorator.

    This generates a decorator that ensures a request-handler is only executed
    if its one if its field (named `field_name`) matches a given value.

    As an example, if this is called with `field_name`='index' and 'field_value'=3,
    this modifies `func` so it is only executed for requests with an index of 3.

    Args:
        func        : The handler function to wrap.
        field_name  : The name of the field to check.
        field_value : The value the given field must have for the function to execute.

        match_index : If true, the matcher is further refined in order to only execute
                       for requests targeting a given e.g. interface or endpoint object.

                       In this case, the handler is only executed if the low byte of the
                       function's index matches the owning object's identifier, as verified
                       with `matches_identifier`.
    """

    @functools.wraps(func)
    def _wrapped(caller, request):

        # Compute our two conditions...
        field_matches = (getattr(request, field_name) == field_value)
        index_matches = \
            caller.matches_identifier(request.index & 0xff) \
            if hasattr(caller, "matches_identifier") and match_index else True

        # ... and call the inner function only if they match.
        if field_matches and index_matches:
            func(caller, request)

        # Otherwise, raise NotImplemented, which translates to a "not handled here".
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
        """ Primary execution; calls the relevant handler if our conditions are met. """

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

        Args:
            field_name : The property of the USBControlRequest object to be checked.
            field_value : The value the relevant property must match to be called.
        """
        matcher = lambda req : getattr(req, field_name) == field_value
        self.add_condition(matcher)


    def __repr__(self):
        return f"<ControlRequestHandler wrapping {self._handler.__qualname__} at 0x{id(self):x}"



def control_request_handler(condition=lambda _ : True, **kwargs):
    """ Decorator that declares a control request handler.

    Used while defining a USBDevice, USBInterface, USBEndpoint, or
    USBOtherRecipient class to declare handlers for that function.

    Args:
        condition : A function that, when evaluated on a USBControlRequest, evaluates
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

def to_this_endpoint(func):
    """ Decorator; refines a handler so it's only called on requests targeting this endpoint. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.ENDPOINT, match_index=True)

def to_any_endpoint(func):
    """ Decorator; refines a handler so it's only called on requests with an endpoint recipient. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.ENDPOINT)

def to_this_interface(func):
    """ Decorator; refines a handler so it's only called on requests targeting this interface. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.INTERFACE, match_index=True)

def to_any_interface(func):
    """ Decorator; refines a handler so it's only called on requests with an interface recipient. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.INTERFACE)

def to_other(func):
    """ Decorator; refines a handler so it's only called on requests with an Other (TM) recipient. """
    return _wrap_with_field_matcher(func, 'recipient', USBRequestRecipient.OTHER)


#
# Metaprogramming aides.
#

def get_request_handler_methods(cls) -> List[callable]:
    """ Returns a list of all handler methods on a given class or object.

    This is used to find all methods of an object decorated with the
    @*_request_handler decorators.
    """

    members = inspect.getmembers(cls)
    return [m for _, m in members if isinstance(m, ControlRequestHandler)]


#
# Control request definitions.
#

@dataclass
class USBControlRequest:
    """ Class encapsulating a USB control request.

    TODO: document parameters
    """

    direction    : USBDirection
    type         : USBRequestType
    recipient    : USBRequestRecipient

    number       : int
    value        : int
    index        : int
    length       : int

    data         : bytes = b""
    device       : USBDescribable = None


    @classmethod
    def from_raw_bytes(cls, raw_bytes: bytes, *, device = None):
        """ Creates a request object from a sequence of raw bytes.

        Args:
            raw_bytes : The raw bytes to create the object from.
            device    : The USBDevice to associate with the given request.
                         Optional, but necessary to use the .reply() / .acknowledge()
                         methods.
        """

        # FIXME: parse using construct
        fields = {
            'direction': (raw_bytes[0] >> 7) & 0b1,
            'type':      (raw_bytes[0] >> 5) & 0b11,
            'recipient': (raw_bytes[0] >> 0) & 0b11111,

            'number':    raw_bytes[1],
            'value':     (raw_bytes[3] << 8) | raw_bytes[2],
            'index':     (raw_bytes[5] << 8) | raw_bytes[4],
            'length':    (raw_bytes[7] << 8) | raw_bytes[6],
            'data':      raw_bytes[8:],
            'device':    device
        }
        return cls(**fields)


    #
    # I/O API.
    #

    def reply(self, data: bytes):
        """ Replies to the given request with a given set of bytes. """
        self.device.control_send(endpoint_number=0, in_request=self, data=data)


    def acknowledge(self, *, blocking: bool = False):
        """ Acknowledge the given request without replying.

        Args:
            blocking : If true, the relevant control request will complete before returning.
        """
        self.device.control_send(endpoint_number=0, in_request=self, data=b"", blocking=blocking)


    def ack(self, *, blocking: bool = False):
        """ Acknowledge the given request without replying.

        Convenience alias for .acknowledge().

        Args:
            blocking : If true, the relevant control request will complete before returning.

        """
        self.acknowledge(blocking=blocking)


    def stall(self):
        """ Stalls the associated device's control request.

        Used to indicate that a given request isn't supported;
        or isn't supported with the provided arguments.
        """
        # Always stall IN endpoint for control requests
        self.device.stall(endpoint_number=0, direction=USBDirection.IN)


    #
    # Properties.
    #


    @property
    def request(self) -> int:
        warnings.warn('`request` should be replaced with `number`', DeprecationWarning)
        return self.number

    @property
    def request_type(self) -> int:
        """ Fetches the whole `request_type` byte. """
        return (self.direction << 7) | \
               (self.type      << 5) | \
               (self.recipient << 0)

    @property
    def value_low(self) -> int:
        return self.value & 0xff

    @property
    def value_high(self) -> int:
        return self.value >> 8

    @property
    def index_low(self) -> int:
        return self.index & 0xff

    @property
    def index_high(self) -> int:
        return self.index >> 8

    def get_direction(self) -> USBDirection:
        return self.direction

    def get_type(self) -> USBRequestType:
        return self.type

    def get_recipient(self) -> USBRequestRecipient:
        return self.recipient


    def raw(self) -> bytes:
        """ Returns the raw bytes that compose the request. """

        # FIXME: use construct?
        b = bytes([ self.request_type, self.number,
                    self.value  & 0xff, (self.value  >> 8) & 0xff,
                    self.index  & 0xff, (self.index  >> 8) & 0xff,
                    self.length & 0xff, (self.length >> 8) & 0xff
                  ])
        return b

    #
    # Pretty printing & log output.
    #
    def __str__(self):

        direction = USBDirection(self.direction).name
        type_name = USBRequestType(self.type).name
        recipient = USBRequestRecipient.from_integer(self.recipient).name
        name      = f"0x{self.number:02x}"

        # If this is a standard request, try to convert it to a name.
        if self.type == USBRequestType.STANDARD:
            try:
                name = f"{USBStandardRequests(self.number).name} (0x{self.number:02x})"
            except ValueError:
                pass

        return f"{direction} {type_name} request {name} to {recipient} " \
                f"[value=0x{self.value:04x}, index=0x{self.index:04x}, length={self.length}]"



class USBRequestHandler(metaclass=ABCMeta):
    """ Base class for any object that handles USB requests. """


    @abstractmethod
    def _request_handlers(self) -> Iterable[callable]:
        """ Returns an iterable of request handlers provided by the class. """


    def _get_subordinate_handlers(self) -> Iterable[callable]:
        """ Returns an iterable of subordinate handlers who should have an opportunity to handle requests.

        Normally called by _call_subordinate_handlers; may not be valid if that function is overridden.
        """
        return ()


    def _call_subordinate_handlers(self, request: USBControlRequest) -> bool:
        """ Calls the ``handle_request`` method of any subordinate handlers.

        This default implementation uses get_subordinates to get an iterable
        of subordinates we should call handle_request on.

        Returns:
            true iff the request is handled
        """

        handled = False

        for configuration in self._get_subordinate_handlers():
            handled = handled or configuration.handle_request(request)

        return handled



    def handle_request(self, request: USBControlRequest) -> bool:
        """ Core control request handler.

        This function can be overridden by a subclass if desired; but the typical way to
        handle a specific control request is to the the ``@control_request_handler`` decorators.

        Args:
            request : the USBControlRequest object representing the relevant request

        Returns:
            true iff the request is handled
        """

        handled = False

        # Our default implementation is simple: we try every handler; allowing any
        # handler that wants to handle the relevant function a chance to handle it.
        #
        # Calling the handler for _every_ matching request (as opposed to e.g. the first one)
        # allows one to trivially add observers.
        for handler in self._request_handlers():
            handled = handler(self, request) or handled

        # Pass our requests down to our subordinates, as well.
        handled = self._call_subordinate_handlers(request) or handled
        return handled
