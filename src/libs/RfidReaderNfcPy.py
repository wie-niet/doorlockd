from .base import DoorlockdBaseClass, dc, baseTriggerAction
from .tools import hwid2hexstr
import time
import threading

import nfc
from nfc.clf import RemoteTarget


class RfidReaderNfcPy(DoorlockdBaseClass):
	# config_name required for DoorlockdBaseClass
	config_name = 'rfid_nfcpy'
	default_status = True
		
	# config path + device
	# usb[:vendor[:product]] / usb[:bus[:device]] / tty:port:driver / com:port:driver / udp[:host][:port]
	path = 'ttyS2:pn532'
	
	# internals
	counter = 0				# nice for statistics
	clf = None				# ContactlessFrontend Object
	stop_loop = True		# tag_detect loop
	thread = None			# thread object
	
	bool_reader	= True		# read NFC tag , set to False to disable reader.
	
	
	
	def __init__(self, start_thread=True):
		
		# get config or defaults
		self.path = self.config.get('path', self.path)

		self.default_status = self.config.get('default_status', self.default_status)
		
		self.hw_init()

		# start thread if self.default_status = True
		if start_thread:
			if self.default_status:
				self.start_thread()
	
	
	def hw_init(self):
		# hw_init RFID reader
		self.clf = nfc.ContactlessFrontend(self.path)
		self.logger.info('NFC RfidReaderNfcPy starting up ({:s}) path: {:s}.'.format(self.log_name, self.path))
	
	# is the thread loop running?
	@property
	def status(self):
		if isinstance(self.thread, threading.Thread):
			if self.thread.isAlive():
				return(True)
				
		# in all other cases: 
		return(False)
		
	# start/stop the thread loop.
	@status.setter
	def status(self, state):
		if state is self.status:
			self.logger.info('notice: {:s}: status update ignored ( status is already {:s})'.format(self.log_name, str(state)))
		else:	
			if state:
				self.start_thread()
			else:
				self.stop_thread()
	
			
	def start_thread(self):	
		if not self.status:
			self.thread = threading.Thread(target=self.run, args=())
			self.thread.daemon = True	# Daemonize thread
			self.thread.start()			# Start the execution
			self.logger.info('start_thread {:s}'.format(self.log_name))
			
		else:
			self.logger.info('notice: {:s}: start_thread, thread is already running '.format(self.log_name))
			
		
	
	def stop_thread(self):
		# stop the loop
		self.stop_loop = True
		self.logger.info('stop_thread {:s}'.format(self.log_name))
		
		
		 
	def callback_tag_detected(self, hwid):
		'''Overwrite this callback method with your own.
			
		def callback_tag_detected(hwid):
			# hwid = [255,255,255,255]
		
			# lookup hwid in db
			# if has_access:
			# 	solenoid.trigger()
		
		'''
		self.logger.debug('{:s} callback_tag_detected({:s}).'.format(self.log_name, str(hwid)))
		# raise NotImplementedError('method callback_tag_detected not implemented')
		

	def run(self):
		'''threading run()'''
		self.logger.info('run detect loop started ({:s}).'.format(self.log_name))
		self.stop_loop = False
		
		
		while not self.stop_loop:
			dc.e.raise_event('rfid_ready') # when rfid starts detecting
			self.io_wait_for_tag_detected()
			dc.e.raise_event('rfid_stopped') # when rfid is stopped detecting

		

	def io_wait_for_tag_detected(self):
		'''start RFID reader and wait , callback_tag_detected() is run when a tag is detected. 
		'''
		
		# target = self.clf.sense(RemoteTarget('106A'), RemoteTarget('106B'), RemoteTarget('212F'))
		target = self.clf.connect(rdwr={'on-connect': lambda tag: False, iterations: 2}, 
									terminate=lambda: self.stop_loop)
			
		# dc.e.raise_event('rfid_comm_pulse') # when there is any RFID communication
		
		if target is False:
			# let's see how often this happens:
			self.logger.info("Some error occured (target==False), re-connecting clf in 1 sec. targe=" + str(target))
			time.sleep(1)
			# hw error ??
			# lets fix:
			
			# Calls close on nfc frontend
			self.clf.close()
			# reconnect:
			self.hw_init()
			
		elif target is not None:
			# TODO: (hwid)
			dc.e.raise_event('rfid_comm_pulse') # when there is any RFID communication
			dc.e.raise_event('rfid_comm_ready') # when there is any RFID communication
			self.logger.debug("HWID: " + str(target))
			
			print("debug test type: ", type(target))
			print("debug test id..: ", str(target.identifier))
			print("debug test hexs: ", hwid2hexstr(target.identifier))
			
			# 
			self.callback_tag_detected(target)
			
			# track statistics
			self.counter = self.counter + 1
			
		# else:
		# 	# error?
		# 	dc.e.raise_event('rfid_comm_error') # when there is any RFID communication error
		# 	self.logger.debug('Error ' + self.__class__.__name__+ ': error return by clf.sense() :')
			


	def hw_exit(self):
		self.logger.debug('cleanup ' + self.__class__.__name__+ ': calling stop.thread & clf.close() ')
		
		# stop internal thread
		self.stop_thread() 
		self.thread.join() # blocking wait for thread to stop.
		
		# # Calls close on nfc frontend
		# self.clf.close() # disabled , seems buggy
		

		


class RfidActions(DoorlockdBaseClass):
	trigger_action = 'open_door'
	config_name = 'rfid_action'
	counter = 0

	def __init__(self):
		# get config or defaults
		self.trigger_action = self.config.get('trigger_action', self.trigger_action)
		
	
	def callback_tag_detected(self, target):
		print("DEBUG: ", target)
		print("DEBUG: ", target.identifier)
		print("DEBUG: ", hwid2hexstr(target.identifier))
		
		hwid_str = hwid2hexstr(target.identifier) # make hwid in hex lowercase string format

		if dc.api.lookup_detected_hwid(hwid_str):
			self.logger.info('{:s} hwid ({:s}) access alowed.'.format(self.log_name, hwid_str))
			dc.e.raise_event('rfid_access_allowed') # raise when rfid is access_allowed
			self.trigger()
		else:
			self.logger.info('{:s} hwid ({:s}) access denied.'.format(self.log_name, hwid_str))
			dc.e.raise_event('rfid_access_denied') # raise when rfid is access_denied, will folow by ..._fin in x seconds
			time.sleep(1)
			dc.e.raise_event('rfid_access_denied_fin') # raise when rfid is access_denied after sleeping x seconds.
			
		
		
	def trigger(self):		
		# raise trigger_action event:
		dc.e.raise_event(self.trigger_action, {'wait': True}) # raise configured trigger_action for rfid_action
		self.counter = self.counter + 1
