import simpy

class Tracker(object):
    """docstring for Tracker"""
    dev_mess = {}
    def __init__(self, arg):
        super(Tracker, self).__init__()
        self.arg = arg
    def add(self, dev_id, time, message):
        if dev_id in dev_mess.keys():
            dev_mess[dev_id].append((time, message))
        else:
            dev_mess[dev_id] = [(time, message)]
    def remove(self, dev_id):
        dev_mess[dev_id] = None