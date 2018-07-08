'''
This module contains helpers for fuzzing
'''

import traceback
import binascii
import inspect


class StageLogger(object):

    def __init__(self, filename):
        self.filename = filename
        self.fd = None

    def start(self):
        self.fd = open(self.filename, 'wb')

    def stop(self):
        if self.fd:
            self.fd.close()

    def log_stage(self, stage):
        if self.fd:
            self.fd.write(stage + '\n')
            self.fd.flush()


stage_logger = StageLogger('dummy')


def set_stage_logger(logger):
    '''
    Set a new stage logger
    '''
    global stage_logger
    stage_logger = logger


def log_stage(stage):
    global stage_logger
    stage_logger.log_stage(stage)


def mutable(stage, silent=False):
    def wrap_f(func):
        func_self = None
        if inspect.ismethod(func):
            func_self = func.im_self
            func = func.im_func

        def wrapper(*args, **kwargs):
            if func_self is None:
                self = args[0]
                args = tuple(args[1:])
            else:
                self = func_self
            response = None
            valid_req = kwargs.get('valid', False)
            info = self.info if not silent else self.debug
            if not valid_req:
                log_stage(stage)
                session_data = self.get_session_data(stage)
                data = kwargs.get('fuzzing_data', {})
                data.update(session_data)
                response = self.get_mutation(stage=stage, data=data)
            try:
                if response is not None:
                    if not silent:
                        info('Got mutation for stage %s' % stage)
                else:
                    if valid_req:
                        info('Calling %s' % (func.__name__))
                    else:
                        info('Calling %s (stage: "%s")' % (func.__name__, stage))
                    response = func(self, *args, **kwargs)
            except Exception as e:
                self.logger.error(traceback.format_exc())
                self.logger.error(''.join(traceback.format_stack()))
                raise e
            if response is not None:
                info('Response: %s' % binascii.hexlify(response))
            return response
        return wrapper
    return wrap_f
