from . import interface 
from .. import IOWrapper as IO
import gpiod

import sys
import threading


# logger = dc.logger
import logging
logger = logging.getLogger(__name__)

#
#  gpiod IOChip and IOPort interface
#


# https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/tree/bindings/python/examples

class IOPort(interface.IOPort):
	pass
	
	
class IOChip(interface.IOChip):
	__io_port_class = IOPort # you need this line , so it will call the above IOPort class
	
	def setup(self, port,  direction):
		"""setup as INPUT: 0/OUTPUT: 1"""

		# consumer
		consumer = sys.argv[0]

		# parse port name:
		(chip_name, line_number) = port.pin.split(' ', 1)

		# gpiod logic:
		port.gpiod_chip = gpiod.Chip(chip_name)
		port.gpiod_line = port.gpiod_chip.get_line(int(line_number))		

		if direction == IO.INPUT:
			# setup INPUT
			# disabled DEBUG testing
			port.gpiod_line.request(consumer=consumer, type=gpiod.LINE_REQ_DIR_IN)
			
			# set identity:
			port.has_input = True
			port.has_output = False
	
		if direction == IO.OUTPUT:
			# # setup OUTPUT, let's asume default value should be 0
			# port.gpiod_line.request(consumer=consumer, type=gpiod.LINE_REQ_DIR_OUT, default_val=0)
			port.gpiod_line.request(consumer=consumer, type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0]) 
			
			# set identity:
			port.has_input = True
			port.has_output = True
			
					
		
	def input(self, port):
		# do whatever you do to get input value for 'pin':
		return port.gpiod_line.get_value()
		

	def output(self, port, value):
		# do whatever you do to set output value for 'pin':
		port.gpiod_line.set_value(value)

	def add_event_detect(self, port, edge, callback):
		# get or init GpiodEventDetectBus
		if not hasattr(port, 'gpiod_events'):
			port.gpiod_events = GpiodEventDetectBus(port)
		
		# events add
		port.gpiod_events.add(edge, callback)
		
	def remove_event_detect(self,port, edge=None, callback=None):
		# events remove
		if hasattr(port, 'gpiod_events'):
			port.gpiod_events.remove(edge, callback)

		
	def cleanup(self, port=None):
		if port:
			# release gpio line.
			port.gpiod_line.release()
			port.gpiod_chip.close()
			
			# one specific pin
			if hasattr(port, 'gpiod_events'):
				port.gpiod_events.cleanup()
		
		if port is None:
			# all pins:
			# not solution for this one.
			pass
	
class GpiodEventDetect:
	def __init__(self, bus, edge, callback):
		self.bus = bus
		self.edge = edge
		self.callback = callback
	
	def stop(self):
		'''remove myself from the event detect bus'''
		self.bus.remove(self.edge, self.callback)

class GpiodEventDetectBus:

	def __init__(self, port):
		self.port = port
		
		# event bus
		self.bus_rising = [] 
		self.bus_falling = []
	
		# boolean to stop _run loop
		self.wait = None
		
		# thread
		self.thread = None

		# lock for adding/removeing events
		self.lock = threading.Lock()
	
	def add(self, edge, callback):
		start_thread = False
		
		with self.lock:
			# add event callback
			if edge == IO.EDGE_RISING:
				self.bus_rising.append(callback)
			elif edge == IO.EDGE_FALLING:
				self.bus_falling.append(callback)
			elif edge == IO.EDGE_BOTH:
				# both
				self.bus_rising.append(callback)
				self.bus_falling.append(callback)
			else:
				raise ValueError("Unkown edge value.")
				return None
		
			# start thread (if needed)
			self._start()
			
		return GpiodEventDetect(self, edge, callback)	
			
	
				
				
	def remove(self, edge=None, callback=None):	
		with self.lock:
			# filter matching edge= callbacks= 
			if callback is None:
				if edge == IO.EDGE_RISING:
					self.bus_rising = [] 
				elif edge == IO.EDGE_FALLING:
					self.bus_falling = []
				elif edge == IO.EDGE_BOTH:
					# get callbacks listed in both
					for cb in self.bus_rising:
						if cb in self.bus_falling:
							self.bus_rising.remove(cb)
							self.bus_falling.remove(cb)
				elif edge is None:
					# cleanup all callbacks
					self.bus_rising = [] 
					self.bus_falling = []
				else:
					raise ValueError("Unkown edge value.")	
			else:	
				# remove event callback
				if edge == IO.EDGE_RISING:
					self.bus_rising.remove(callback)
				elif edge == IO.EDGE_FALLING:
					self.bus_falling.remove(callback)
				elif edge == IO.EDGE_BOTH:
					# both
					self.bus_rising.remove(callback)
					self.bus_falling.remove(callback)
				else:
					raise ValueError("Unkown edge value.")

			# stop thread (if needed)
			if len(self.bus_rising) == 0 and len(self.bus_falling) == 0:
				# stop the loop 
				self.wait = False
		
			
	def _start(self):
		# enable the while loop
		self.wait = True
		
		# start thread when needed:
		if self.thread is None:
			# start _run in new thread:
			self.thread = threading.Thread(target=self._run, daemon=True)
			self.thread.start()
		

	def _run(self):
		# parse port name:
		(chip_name, line_number) = self.port.pin.split(' ', 1)

		# gpiod logic:
		gpiod_chip = gpiod.Chip(chip_name)
		self.gpiod_line = gpiod_chip.get_line(int(line_number))
		
		# consumer
		consumer = sys.argv[0]
		
		# update our gpiod_line:
		self.port.gpiod_line.release() # release
		self.port.gpiod_line.request(consumer=consumer, type=gpiod.LINE_REQ_EV_BOTH_EDGES)
		self.gpiod_line = self.port.gpiod_line # link line from port object.

		logger.debug("event detect loop starting for pin '{}'.".format(self.port.pin))

		# run main detect loop 
		while self.wait:
			if self.gpiod_line.event_wait(1) and self.wait:
				event = self.gpiod_line.event_read()
				
				if event.type == gpiod.LineEvent.RISING_EDGE:
					 for callback in self.bus_rising:
						 callback()

				if event.type == gpiod.LineEvent.FALLING_EDGE:
					 for callback in self.bus_falling:
						 callback()
						 
				# call callback
				# print ("DEBUG: call callbacks ", self.port.pin_name, "event=", event)
			# else:
				# print("DEBUG: ", self.port.pin, "timeout(1s) ")

		logger.debug("event detect loop stoppped for pin '{}'.".format(self.port.pin))

		with self.lock:
			self.gpiod_line.release()

			# do we really need to stop?
			if self.wait is not True:
				self.thread = None		

			else:
				# aparently a new callback has been added while we got out of the loop, no worries we will restart ourselfs:
				self._run()

			
	def cleanup(self):
		with self.lock:
			# event bus
			self.bus_rising = [] 
			self.bus_falling = []
	
			# boolean to stop _run loop
			self.wait = False
		
		