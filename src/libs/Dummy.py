from .base import baseTriggerAction

#
# Dummy trigger action, can be assigned as trigger_action on Buttons
#	
class Dummy(baseTriggerAction):
	"""this dummy trigger really does nothing."""
	config_name = 'Dummy'
	
	def trigger(self, wait=None):
		self.logger.debug('{:s} trigger()'.format(self.log_name))
		pass
	
	
	