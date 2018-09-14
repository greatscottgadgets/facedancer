#!/usr/bin/env python
'''
Prepare stages for USB fuzzing

Usage:
    umap2makestages -P=PHY_INFO -C=DEVICE_CLASS -s=FILE [-q] [--vid=VID] [--pid=PID] [-v ...]

Options:
    -P --phy PHY_INFO       physical layer info, see list below
    -C --class DEVICE_CLASS class of the device or path to python file with device class
    -s --stage-file FILE    file to store list of stages in
    -q --quiet              quiet mode. only print warning/error messages
    -v --verbose            verbosity level
    --vid VID               override vendor ID
    --pid PID               override product ID

Physical layer:
    fd:<serial_port>        use facedancer connected to given serial port
    gadgetfs                use gadgetfs (requires mounting of gadgetfs beforehand)
'''
import time
from umap2.apps.emulate import Umap2EmulationApp
from umap2.fuzz.helpers import StageLogger, set_stage_logger


class Umap2MakeStagesApp(Umap2EmulationApp):

    def load_device(self, dev_name, phy):
        self.start_time = time.time()
        self.stage_file_name = self.options['--stage-file']
        stage_logger = StageLogger(self.stage_file_name)
        stage_logger.start()
        set_stage_logger(stage_logger)
        return super(Umap2MakeStagesApp, self).load_device(dev_name, phy)

    def should_stop_phy(self):
        stop_phy = False
        passed = int(time.time() - self.start_time)
        if passed > 5:
            self.logger.info('have been waiting long enough (over %d secs.), disconnect' % (passed))
            stop_phy = True
        return stop_phy


def main():
    app = Umap2MakeStagesApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()
