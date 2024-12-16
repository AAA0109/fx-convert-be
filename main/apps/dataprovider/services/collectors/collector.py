from random import randint, uniform


# =====================================

class BaseCollector:

    def __init__(self, collector, source, cache=None, publisher=None, writer=None, **kwargs):

        self.collector = collector
        self.source = source
        self.cache = cache() if cache else None
        self.publisher = publisher() if publisher else None
        self.writer = writer() if writer else None

        # local caches
        self.factories = {}
        self.last = {}

        # if we want to use sampling... set the sampling rate
        self.global_sampling = 1.0
        self.pub_sampling = 1.0
        self.write_sampling = 1.0
        self.cache_sampling = 1.0
        self.sample_pool = None

        # set sample rates
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    # coudl generate a pool of random floats, if float <= sample_rate, perform action
    # if pool runs out, refill

    # ===========================

    def register_factory(self, key, factory):

        # ensure message is well formed
        factory.collector = self.collector
        factory.source = self.source

        if key in factories:
            raise KeyError('key already registered')

        self.factories[key] = factory

    def flush(self):
        # could flush self.last as well
        if self.writer: self.writer.flush()

    def close(self):
        if self.writer: self.writer.close()

    # close the other services here

    # ============================

    @staticmethod
    def sample_check(sampling):
        if sampling == 1.0:
            return True
        return (uniform(0.0, 1.0) <= sampling)

    def collect(self, *args, factory=None, factory_key=None, **kwargs):

        # this can run on a schedule or be called by a callback-based system

        if not self.sample_check(self.global_sampling):
            return

        factory = factory or self.factories[factory_key]
        record, bucket, key = factory(*args, **kwargs)

        # save last for flushing
        self.last[bucket] = record

        # if cache first... could change the order
        if self.cache: self.cache.write_record(record, bucket, key)
        if self.writer: self.writer.write_record(record, bucket, key)
        if self.publisher: self.publisher.write_record(record, bucket, key)

        """
        # if cache first...
        if self.sample_check( self.cache_sampling ):
            self.cache.write_record( record, bucket, key )

        # if save first...
        if self.sample_check( self.write_sampling ):
            self.writer.write_record( record, bucket, key )

        if self.sample_check( self.pub_sampling ):
            self.publisher.write_record( record, bucket, key )
        """
        return record
        
