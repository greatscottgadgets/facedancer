#!/usr/bin/env python
'''
Emulate a USB device to be used for fuzzing

Usage:
    umap2fuzz -P=PHY_INFO -C=DEVICE_CLASS [-q] [--vid=VID] [--pid=PID] [-i=FUZZER_IP] [-p FUZZER_PORT] [-v ...]

Options:
    -P --phy PHY_INFO           physical layer info, see list below
    -C --class DEVICE_CLASS     class of the device or path to python file with device class
    -v --verbose                verbosity level
    -i --fuzzer-ip HOST         hostname or IP of the fuzzer [default: 127.0.0.1]
    -p --fuzzer-port PORT       port of the fuzzer [default: 26007]
    -q --quiet                  quiet mode. only print warning/error messages
    --vid VID                   override vendor ID
    --pid PID                   override product ID

Physical layer:
    fd:<serial_port>        use facedancer connected to given serial port
    gadgetfs                use gadgetfs (requires mounting of gadgetfs beforehand)

Examples:
    emulate disk-on-key:
        umap2fuzz -P fd:/dev/ttyUSB1 -C mass_storage
'''
import os
import time
from kitty.remote.rpc import RpcClient
from umap2.apps.emulate import Umap2EmulationApp


class Umap2FuzzApp(Umap2EmulationApp):

    def __init__(self, options):
        super(Umap2FuzzApp, self).__init__(options)
        self.count = 0

    def get_fuzzer(self):
        fuzzer = RpcClient(
            host=self.options['--fuzzer-ip'],
            port=int(self.options['--fuzzer-port'])
        )
        fuzzer.start()
        return fuzzer

    def should_stop_phy(self):
        self.count = (self.count + 1) % 50
        self.check_connection_commands()
        if self.count == 0:
            self.send_heartbeat()
        return False

    def send_heartbeat(self):
        heartbeat_file = '/tmp/umap_kitty/heartbeat'
        if os.path.isdir(os.path.dirname(heartbeat_file)):
            with open(heartbeat_file, 'a'):
                os.utime(heartbeat_file, None)

    def check_connection_commands(self):
        '''
        :return: whether performed reconnection
        '''
        if self._should_disconnect():
            self.phy.disconnect()
            self._clear_disconnect_trigger()
            # wait for reconnection request; no point in returning to service_irqs loop while not connected!
            while not self._should_reconnect():
                self._clear_disconnect_trigger()  # be robust to additional disconnect requests
                time.sleep(0.1)
        # now that we received a reconnect request, flow into the handling of it...
        # be robust to reconnection requests, whether received after a disconnect request, or standalone
        # (not sure this is right, might be better to *not* be robust in the face of possible misuse?)
        if self._should_reconnect():
            self.phy.connect(self.dev)
            self._clear_reconnect_trigger()
            return True
        return False

    def _should_reconnect(self):
        if self.fuzzer:
            if os.path.isfile('/tmp/umap_kitty/trigger_reconnect'):
                return True
        return False

    def _clear_reconnect_trigger(self):
        trigger = '/tmp/umap_kitty/trigger_reconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    def _should_disconnect(self):
        if self.fuzzer:
            if os.path.isfile('/tmp/umap_kitty/trigger_disconnect'):
                return True
        return False

    def _clear_disconnect_trigger(self):
        trigger = '/tmp/umap_kitty/trigger_disconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    def get_mutation(self, stage, data=None):
        if self.fuzzer:
            data = {} if data is None else data
            return self.fuzzer.get_mutation(stage=stage, data=data)
        return None


def main():
    app = Umap2FuzzApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()
