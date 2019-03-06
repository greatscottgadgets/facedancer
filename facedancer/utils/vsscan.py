
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
