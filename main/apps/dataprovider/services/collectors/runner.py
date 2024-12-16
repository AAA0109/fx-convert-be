import time
from itertools import product

from concurrent.futures import ThreadPoolExecutor
from main.apps.oems.backend.utils import sleep_for


# ==============

class CollectorRunner:

    def __init__(self, *args, **kwargs):

        self.cache = []
        self.max_workers = 3

        for collector in args:
            self.cache.append(collector)

    def register_collector(self, collector):
        self.cache.append(collector)

    def cycle_(self, args):
        return args[1].cycle(args[0])

    def cycle(self, now):
        if self.max_workers > 1 and len(self.cache) > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                responses = list(executor.map(self.cycle_, product([now], self.cache)))
        else:
            for collector in self.cache:
                collector.cycle(now)

    def close(self):
        for collector in self.cache:
            collector.close()

    def run_forever(self):
        try:
            while True:
                now = time.time()
                self.cycle(now)
                sleep_for(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.close()


if __name__ == "__main__":
    pass
