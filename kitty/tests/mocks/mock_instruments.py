'''
Instrumentation class for mock classes,
can be used to retrieve additional info about the tests.
'''


class MockInstrumentation(object):

    def __init__(self):
        self.counters = {}
        self.lists = {}

    def count_increment(self, counter_name):
        count = self.counters.get(counter_name, 0)
        self.counters[counter_name] = count + 1

    def count_get(self, counter_name):
        return self.counters.get(counter_name)

    def reset(self, counter_name):
        self.counters[counter_name] = 0

    def list_add(self, list_name, elem):
        lst = self.lists.get(list_name, [])
        lst.append(elem)
        self.lists[list_name] = lst

    def list_clear(self, list_name):
        self.lists[list_name] = []

    def list_get(self, list_name):
        return self.lists.get(list_name)
