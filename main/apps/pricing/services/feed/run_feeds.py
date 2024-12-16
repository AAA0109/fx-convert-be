import logging
import signal
import subprocess
import sys
import time

from main.apps.pricing.models import Feed

logger = logging.getLogger("root")


class RunFeedService(object):

    def execute(self):
        self.processes = {}
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        while True:
            active_feeds = Feed.objects.filter(enabled=True)

            # Start processes for newly enabled feeds
            for feed in active_feeds:
                if feed.id not in self.processes or self.processes[feed.id]['process'].poll() is not None:
                    logger.info(f"Starting feed ID: {feed.id}")
                    process = self._run_feed(feed.id)
                    self.processes[feed.id] = {'process': process, 'enabled': True}

            # Check and terminate processes for feeds no longer enabled
            to_remove = [feed_id for feed_id in self.processes if
                         not Feed.objects.filter(id=feed_id, enabled=True).exists()]
            for feed_id in to_remove:
                logger.info(f"Terminating feed ID: {feed_id}")
                self.processes[feed_id]['process'].terminate()
                self.processes[feed_id]['process'].wait()  # Ensure process is terminated
                del self.processes[feed_id]

            # Print PIDs of running processes
            for feed_id, data in self.processes.items():
                if data['process'].poll() is None:  # Process is still running
                    logger.info(f"Feed ID {feed_id} running with PID: {data['process'].pid}")

            time.sleep(2.0)  # Loop every 2 seconds

    def signal_handler(self, signal_received, frame):
        # Handle any cleanup here
        logger.info('Signal received, terminating all processes...')
        for feed_id, info in self.processes.items():
            info['process'].terminate()
        logger.info('all processes terminated. Exiting...')
        sys.exit(0)

    @staticmethod
    def _run_feed(feed_id):
        command = [
            './manage.py', 'runfeed',
            '--feed-id', str(feed_id),
        ]
        return subprocess.Popen(command)
