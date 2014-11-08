from __future__ import division, print_function
from collections import deque

from simpy.resources.store import Store

class SizedStore(Store):
    """Models the production and consumption of concrete Python objects of 
    variable sizes.

    The *sizefunc* returns the size of an item when applied on it. The return
    value must be a non-negative integer.

    """
    def __init__(self, env, capacity=float('inf'), sizefunc=1):
        super(SizedStore, self).__init__(env, capacity)
        self.items = deque()
        """List of the items within the store."""
        if not hasattr(sizefunc, '__call__'):
            sizefunc = (lambda _: sizefunc)
        self._sizefunc = sizefunc
        self._level = 0

    def _do_put(self, event):
        item = event.item
        size = self._sizefunc(item)
        if (not isinstance(size, (int, long))) or (size < 0):
            raise ValueError('Size of item must be a non-negative integer.')
        if (self._level + size) <= self._capacity:
            self._level += size
            self.items.append(item)
            event.succeed()

    def _do_get(self, event):
        if self.items:
            item = self.items.popleft()
            self._level -= self._sizefunc(item)
            event.succeed(item)
