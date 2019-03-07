# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This example was authored and contributed by dark-lbp <jtrkid@gmail.com>
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
import socket
import threading
import select
import errno
import time
import struct
import random
import traceback
from binascii import hexlify
from kitty.core.kitty_object import KittyObject

host = '0.0.0.0'
port = 9999


def _eintr_retry(func, *args):
    """restart a system call interrupted by EINTR"""
    while True:
        try:
            return func(*args)
        except (OSError, select.error) as e:
            if e.args[0] != errno.EINTR:
                raise


class BaseRequestHandler(KittyObject):
    '''
    Base class for request handler classes.

    This class is instantiated for each request to be handled.  The
    constructor sets the instance variables request, client_address
    and server, and then calls the handle() method.  To implement a
    specific service, all you need to do is to derive a class which
    defines a handle() method.

    The handle() method can find the request as self.request, the
    client address as self.client_address, and the server (in case it
    needs access to per-server information) as self.server.  Since a
    separate instance is created for each request, the handle() method
    can define arbitrary other instance variariables.
    '''

    def __init__(self, name, request, client_address, server, logger=None):
        '''
        :param name: Name of the object
        :param request: TCP socket connected to the client
        :param client_address: Client address of request
        :param server: Session server
        :param logger: Logger for this object (default: None)
        '''

        super(BaseRequestHandler, self).__init__(name, logger)
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def setup(self):
        pass

    def handle(self):
        pass

    def finish(self):
        pass


class BaseServer(KittyObject):
    '''
    Base class for server classes.

    Methods for the caller:

    - __init__(server_address, RequestHandlerClass)
    - serve_forever(poll_interval=0.5)
    - shutdown()
    - handle_request()  # if you do not use serve_forever()
    - fileno() -> int   # for select()

    Methods that may be overridden:

    - server_bind()
    - server_activate()
    - get_request() -> request, client_address
    - handle_timeout()
    - verify_request(request, client_address)
    - server_close()
    - process_request(request, client_address)
    - shutdown_request(request)
    - close_request(request)
    - handle_error()

    Methods for derived classes:

    - finish_request(request, client_address)

    Class variables that may be overridden by derived classes or
    instances:

    - timeout
    - address_family
    - socket_type
    - allow_reuse_address

    Instance variables:

    - RequestHandlerClass
    - socket

    '''
    timeout = None

    def __init__(self, name, server_address, request_handler, logger=None):
        '''
        :param name: Name of the object
        :param server_address: server address for socket to listen
        :param request_handler: class to handle request
        :param logger: Logger for this object (default: None)
        '''

        super(BaseServer, self).__init__(name, logger)
        self.server_address = server_address
        self.request_handler = request_handler
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False

    def server_activate(self):
        """
        Called by constructor to activate the server.
        May be overridden.
        """

        pass

    def serve_forever(self, poll_interval=0.5):
        """
        Handle one request at a time until shutdown.
        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                r, w, e = _eintr_retry(select.select, [self], [], [], poll_interval)
                if self in r:
                    self._handle_request_noblock()

        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def shutdown(self):
        """
        Stops the serve_forever loop.
        Blocks until the loop has finished. This must be called while
        serve_forever() is running in another thread, or it will
        deadlock.
        """
        self.__shutdown_request = True
        self.__is_shut_down.wait()

    def handle_request(self):
        """
        Handle one request, possibly blocking.
        Respects self.timeout.
        """

        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        fd_sets = _eintr_retry(select.select, [self], [], [], timeout)
        if not fd_sets[0]:
            self.handle_timeout()
            return
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        """
        Handle one request, without blocking.
        """

        try:
            request, client_address = self.get_request()
        except socket.error:
            return

        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.shutdown_request(request)

    def handle_timeout(self):
        """
        Called if no new request arrives within self.timeout.
        """
        pass

    def verify_request(self, request, client_address):
        """
        Verify the request.
        Return True if we should proceed with this request.
        """
        return True

    def process_request(self, request, client_address):
        """
        Call finish_request.
        """

        self.finish_request(request, client_address)
        self.shutdown_request(request)

    def server_close(self):
        """
        Called to clean-up the server.
        May be overridden.
        """
        pass

    def finish_request(self, request, client_address):
        """
        Finish one request by instantiating RequestHandlerClass.
        """

        self.request_handler(request, client_address, self)

    def shutdown_request(self, request):
        """
        Called to shutdown and close an individual request.
        """

        self.close_request(request)

    def close_request(self, request):
        """
        Called to clean up an individual request.
        """

        pass

    def handle_error(self, request, client_address):
        """
        Handle an error gracefully.  May be overridden.

        The default is to print a traceback and continue.

        """
        self.logger.error('-' * 40)
        self.logger.error('Exception happened during processing of request from %s:%s' % (client_address[0], client_address[1]))
        self.logger.error(traceback.format_exc())
        self.logger.error('-' * 40)


class TCPServer(BaseServer):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, name, server_address, request_handler, logger=None):
        '''
        :param name: Name of the object
        :param server_address: server address for socket to listen
        :param request_handler: class to handle request
        :param logger: Logger for this object (default: None)
        '''

        super(TCPServer, self).__init__(name, server_address, request_handler, logger)
        self.socket = socket.socket(self.address_family, self.socket_type)

    def server_bind(self):
        """
        Called by constructor to bind the socket.
        """

        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def server_activate(self):
        """
        Called by constructor to activate the server.
        """

        self.socket.listen(self.request_queue_size)

    def server_close(self):
        """
        Called to clean-up the server.
        """

        self.socket.close()

    def fileno(self):
        """
        Return socket file number.
        Interface required by select().
        """

        return self.socket.fileno()

    def get_request(self):
        """
        Get the request and client address from the socket.
        """

        return self.socket.accept()

    def shutdown_request(self, request):
        """
        Called to shutdown and close an individual request.
        """

        try:
            request.shutdown(socket.SHUT_WR)
        except socket.error:
            pass

        self.close_request(request)

    def close_request(self, request):
        """
        Called to clean up an individual request.
        """

        request.close()

    def process_request_thread(self, request, client_address):
        """
        Process the request.
        """

        try:
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except Exception as e:
            self.logger.error(e)
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """
        Start a new thread to process the request.
        """

        t = threading.Thread(target=self.process_request_thread,
                             args=(request, client_address))
        t.daemon = self.daemon_threads
        t.start()


class SessionHandler(BaseRequestHandler):
    '''
    The SessionHandler class for our session server.
    First you need request a session by sending 'get_session' packet to server, server will return same format packet
    with specific session inside.
    After you got the session you can communicate with server by sending 'send_data' packet to server. If your session
    is correct server will return a same packet which you just send, otherwise server will return 'session is incorrect'.
    Remember Session server only support two kind of packet 'get_session' and 'send_data'. If you send other packet to
    server, server will server will return 'packet format is incorrect' and close your current connection.
    Server will stop(fake crash) when you send a large packet(length greater than 255) with 'send_data' format.

    :Example Protocol:

        ::
            Fuzzer (client)                               Target (server)
                ||---------------(get_session)------------------>||
                ||<---------------(session_id)-------------------||
                ||----------(session_id + send_data)------------>||
                ||<---------(session_id + send_data)-------------||
                ||----------(session_id + send_data)------------>||
                ||<---------(session_id + send_data)-------------||
                ||<---------........................-------------||
                ||----------........................------------>||


    :get_session:

        ::
            get_session = Template(name='get_session', fields=[
                UInt8(value=1, name='op_code', fuzzable=False),
                UInt16(value=0, name='session_id', fuzzable=False)
            ])


    :send_data:
        ::
            send_data = Template(name='send_data', fields=[
                UInt8(value=2, name='op_code', fuzzable=False),
                Dynamic(key='session_id', default_value='\x00\x00'),
                String(name='data', value='some data')
            ])

    '''

    def __init__(self, request, client_address, server, name='SessionHandler', logger=None):
        '''
        :param request: TCP socket connected to the client
        :param client_address: Client address of request
        :param server: Session server
        :param name: Name of the object
        :param logger: Logger for the object (default: None)
        '''

        # Create 2 byte specific session for each request
        self._session = struct.pack('H', random.randrange(65535))
        self._recv_data = None
        self._resp_data = None
        super(SessionHandler, self).__init__(name, request, client_address, server, logger)

    def _send_session(self):
        self._resp_data = b'\x01' + self._session
        self.logger.info('Session id is: %s' % hexlify(self._session).decode())
        self.request.send(self._resp_data)
        self._cleanup()

    def _send_data(self, data):
        self.request.send(data)
        self._cleanup()

    def _crash(self):
        raise Exception("Congratulations you successful crash session server!")

    def _check_session(self, data):
        if data[1:3] == self._session:
            return True
        else:
            return False

    def _check_crash(self, data):
        if len(data) > 255:
            return True
        else:
            return False

    def _cleanup(self):
        self._recv_data = None
        self._resp_data = None

    def _close(self):
        self.request.close()
        self.finish()

    def handle(self):
        while True:
            # self.request is the TCP socket connected to the client
            if self.request:
                self._recv_data = self.request.recv(1024).strip()
                if self._recv_data:
                    self.logger.debug('Received data is: %s' % hexlify(self._recv_data).decode())
                    # Check is get_session packet
                    if self._recv_data == b'\x01\x00\x00':
                        self._send_session()
                    # Check is send_data packet
                    elif self._recv_data[0] == b'\x02':
                        if self._check_session(self._recv_data):
                            self.logger.info('session is correct')
                            if self._check_crash(self._recv_data):
                                self._crash()
                                break
                            else:
                                self._send_data(self._recv_data)
                        else:
                            self.logger.info('session is incorrect')
                            self._send_data('session is incorrect')
                            self._close()
                            break
                    else:
                        self.logger.info('Packet format is incorrect')
                        self._close()
                        break
                else:
                    self._close()
                    break
            else:
                break


class SessionServer(TCPServer):
    '''
    SessionServer is implementation of a TCP Server for the ServerFuzzer
    '''

    allow_reuse_address = True

    def __init__(self, name, server_address, request_handler, logger=None):
        '''
        :param name: Name of the object
        :param server_address: server address for socket to listen
        :param request_handler: class to handle request
        :param logger: Logger for this object (default: None)
        '''

        super(SessionServer, self).__init__(name, server_address, request_handler, logger)

    def stop(self):
        self.shutdown()
        self.server_close()
        time.sleep(1)

    def start(self):
        self.server_bind()
        self.server_activate()
        self.serve_forever()

    def handle_error(self, request, client_address):
        """
        Add self.stop to make server stop
        """
        self.logger.error('-' * 40)
        self.logger.error('Exception happened during processing of request from %s:%s' % (client_address[0], client_address[1]))
        self.logger.error(traceback.format_exc())
        self.logger.error('-' * 40)
        self.stop()


if __name__ == '__main__':
    my_server = SessionServer('SessionServer', (host, port), SessionHandler)
    my_server.start()
