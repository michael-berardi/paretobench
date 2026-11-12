"""A replaceable clock so tests never depend on wall time."""
import time


class Clock:
    def __init__(self, start=None):
        self._fixed = start

    def now(self):
        return self._fixed if self._fixed is not None else time.time()

    def advance(self, seconds):
        if self._fixed is None:
            raise RuntimeError("only a fixed clock can be advanced")
        self._fixed += seconds
        return self._fixed


SYSTEM = Clock()
