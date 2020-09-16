# from .data_container import data_container as dc
from .base import hw12vOut, GPIO, baseTriggerAction
import time
import threading

class Buzzer(hw12vOut, baseTriggerAction):
	config_name = 'buzzer'
	time_wait = 0.4
	counter = 0
	
	def __init__(self):
		# read gpio_pin from config
		self.gpio_pin = self.config.get('pin')

		# amount of time the door is open
		self.time_wait = self.config.get('time', self.time_wait)
		
		# hw_init
		self.hw_init()
		

	def event_callback(self, data):
		self.trigger(data.get('wait', False))
		
		
	def trigger(self, wait=False):
		'''turn Buzzer on for self.time seconds. '''
		self.trigger_begin()

		# do we block ot wait in a new thread
		if wait:
			time.sleep(self.time_wait)
			self.trigger_end()
		else:
			t = threading.Timer(self.time_wait, self.trigger_end)
			t.start()  # after self.time_wait seconds, trigger_end() will be executed

	def trigger_begin(self):
		'''turn Buzzer on for start'''
		# self.deamon = True
		self.logger.debug('{:s} open.'.format(self.log_name))
		self.counter = self.counter + 1

		#
		# set GPIO_PIN high for x amount of time
		#
		GPIO.output(self.gpio_pin, GPIO.HIGH)



	def trigger_end(self):
		'''Buzzer  end. '''
		# # if self.ui is not None:
		# 	# self.ui.ui_on_door_open()
		#
		# time.sleep(self.time_wait)
		GPIO.output(self.gpio_pin, GPIO.LOW)
		#
		# if self.ui is not None:
		# 	self.ui.ui_off_door_open()


		self.logger.debug('{:s} close.'.format(self.log_name))



