import logging

stdio_handler = None
facedancer_logger = None


def prepare_logging():
    global facedancer_logger
    global stdio_handler
    if facedancer_logger is None:
        def add_debug_level(num, name):
            def fn(self, message, *args, **kwargs):
                if self.isEnabledFor(num):
                    self._log(num, message, args, **kwargs)
            logging.addLevelName(num, name)
            setattr(logging, name, num)
            return fn

        logging.Logger.verbose = add_debug_level(5, 'VERBOSE')
        logging.Logger.always = add_debug_level(100, 'ALWAYS')

        FORMAT = '[%(levelname)-6s] %(message)s'
        stdio_handler = logging.StreamHandler()
        stdio_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(FORMAT)
        stdio_handler.setFormatter(formatter)
        facedancer_logger = logging.getLogger('facedancer')
        facedancer_logger.addHandler(stdio_handler)
        facedancer_logger.setLevel(logging.VERBOSE)
    return facedancer_logger


def set_default_handler_level(level):
    global stdio_handler
    stdio_handler.setLevel(level)
