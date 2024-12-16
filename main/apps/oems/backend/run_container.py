import os
import signal
import logging
import time

from django.conf import settings

from main.apps.oems.backend.utils  import sleep_for

class RunContainer:

	def __init__( self, timeout=1.0 ):

		self.services = {}
		self._timeout  = timeout
		self._kill_sig = False

		# shutdown signals
		signal.signal(signal.SIGINT, self.on_shutdown)
		signal.signal(signal.SIGTERM, self.on_shutdown)

	def on_shutdown( self, *args ):
		self._kill_sig = True

	def add_service( self, service_name, service ):
		# could add config for how often to do stuff
		self.services[service_name] = service

	def run( self ):
		try:
			while not self._kill_sig:
				# cycle all the services
				for service in self.services.values():
					service.cycle()
				if isinstance(self._timeout, float): sleep_for(self._timeout)
		except KeyboardInterrupt:
			pass

		return 0