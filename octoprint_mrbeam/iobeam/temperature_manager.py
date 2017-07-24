
import threading
import time
from octoprint.events import Events as OctoPrintEvents
from octoprint_mrbeam.mrbeam_events import MrBeamEvents
from octoprint_mrbeam.iobeam.iobeam_handler import IoBeamEvents
from octoprint_mrbeam.mrb_logger import mrb_logger


# singleton
_instance = None

def temperatureManager():
	global _instance
	if _instance is None:
		_instance = TemperatureManager()
	return _instance

# This guy manages the temperature of the laser head
class TemperatureManager(object):

	TEMP_TIMER_INTERVAL = 3
	TEMP_MAX_AGE = 10 # seconds

	def __init__(self):
		self._logger = mrb_logger("octoprint.plugins.mrbeam.iobeam.temperaturemanager")

		self.temperature = None
		self.temperature_ts = time.time()
		self.temperature_max = _mrbeam_plugin_implementation.laserCutterProfileManager.get_current_or_default()['laser']['max_temperature']
		self.hysteresis_temperature = _mrbeam_plugin_implementation.laserCutterProfileManager.get_current_or_default()['laser']['hysteresis_temperature']
		self.temp_timer = None
		self.is_cooling_since = 0

		self._shutting_down = False

		self._subscribe()
		self._start_temp_timer()

	def _subscribe(self):
		_mrbeam_plugin_implementation._event_bus.subscribe(IoBeamEvents.LASER_TEMP, self.onEvent)
		_mrbeam_plugin_implementation._event_bus.subscribe(OctoPrintEvents.PRINT_DONE, self.onEvent)
		_mrbeam_plugin_implementation._event_bus.subscribe(OctoPrintEvents.PRINT_FAILED, self.onEvent)
		_mrbeam_plugin_implementation._event_bus.subscribe(OctoPrintEvents.PRINT_CANCELLED, self.onEvent)
		_mrbeam_plugin_implementation._event_bus.subscribe(OctoPrintEvents.SHUTDOWN, self.onEvent)

	def shutdown(self):
		self._shutting_down = True

	def reset(self):
		self.temperature_max = _mrbeam_plugin_implementation.laserCutterProfileManager.get_current_or_default()['laser']['max_temperature']
		self.hysteresis_temperature = _mrbeam_plugin_implementation.laserCutterProfileManager.get_current_or_default()['laser']['hysteresis_temperature']
		self.is_cooling_since = 0
		self.send_cooling_state_to_frontend(self.is_cooling())

	def onEvent(self, event, payload):
		if event == IoBeamEvents.LASER_TEMP:
			self.handle_temp(payload)
		elif event in (OctoPrintEvents.PRINT_DONE, OctoPrintEvents.PRINT_FAILED, OctoPrintEvents.PRINT_CANCELLED):
			self.reset()
		elif event == OctoPrintEvents.SHUTDOWN:
			self.shutdown()

	def handle_temp(self, payload):
		temp = payload['val'] if 'val' in payload else None
		self.temperature = temp
		self.temperature_ts = time.time()
		self._check_temp_val()
		self.send_status_to_frontend(self.temperature)

	def request_temp(self):
		_mrbeam_plugin_implementation._ioBeam.send_command("laser:temp")

	def cooling_stop(self):
		if  _mrbeam_plugin_implementation._oneButtonHandler.is_printing():
			self._logger.debug("cooling_stop()")
			self.is_cooling_since = time.time()
			_mrbeam_plugin_implementation._oneButtonHandler.cooling_down_pause()
			_mrbeam_plugin_implementation._event_bus.fire(MrBeamEvents.LASER_COOLING_PAUSE, dict(temp=self.temperature))
			self.send_cooling_state_to_frontend(True)
		else:
			self._logger.debug("cooling_stop() skipping because printer state is not Printing: %s", _mrbeam_plugin_implementation._printer.get_state_id())

	def cooling_resume(self):
		self._logger.debug("cooling_resume()")
		_mrbeam_plugin_implementation._event_bus.fire(MrBeamEvents.LASER_COOLING_RESUME, dict(temp=self.temperature))
		_mrbeam_plugin_implementation._oneButtonHandler.cooling_down_end(only_if_behavior_is_cooling=True)
		self.is_cooling_since = 0

	def is_cooling(self):
		return (self.is_cooling_since is not None and self.is_cooling_since > 0)

	def is_temperature_recent(self):
		if self.temperature is None:
			self._logger.error("is_temperature_recent(): Laser temperature is None. never received a temperature value.")
			return False
		age = time.time() - self.temperature_ts
		if age > self.TEMP_MAX_AGE:
			self._logger.error("is_temperature_recent(): Laser temperature too old: must be more recent than %s s but actual age is %s s",
			                   self.TEMP_MAX_AGE, age)
			return False
		return True

	def _temp_timer_callback(self):
		try:
			self.request_temp()
			self._stop_if_temp_is_not_current()
			self._start_temp_timer()
		except:
			self._logger.exception("Exception in _temp_timer_callback(): ")
			# this might have been the reason for the exception. Let's try to stay alive anyway...
			self._start_temp_timer()

	def _start_temp_timer(self):
		if not self._shutting_down:
			self.temp_timer = threading.Timer(self.TEMP_TIMER_INTERVAL, self._temp_timer_callback)
			self.temp_timer.daemon = True
			self.temp_timer.name = "TemperatureTimer"
			self.temp_timer.start()
		else:
			self._logger.debug("Shutting down.")

	def _stop_if_temp_is_not_current(self):
		if not self.is_temperature_recent():
			self._logger.error("_stop_if_temp_is_not_current() Laser temperature is not recent. Stopping laser.")
			self.cooling_stop()

	def _check_temp_val(self):
		if not self.is_cooling() and (self.temperature is None or self.temperature > self.temperature_max):
			self._logger.warn("Laser temperature exceeded limit. Current temp: %s, max: %s", self.temperature, self.temperature_max)
			self.cooling_stop()
		elif self.is_cooling() and self.temperature is not None and self.temperature <= self.hysteresis_temperature:
			self._logger.warn("Laser temperature passed hysteresis limit. Current temp: %s, hysteresis: %s", self.temperature, self.hysteresis_temperature)
			self.cooling_resume()
		else:
			# self._logger.debug("Laser temperature nothing. Current temp: %s, self.is_cooling(): %s", self.temperatur, self.is_cooling())
			pass

	def send_cooling_state_to_frontend(self, cooling):
		_mrbeam_plugin_implementation._plugin_manager.send_plugin_message("mrbeam", dict(cooling=cooling))

	def send_status_to_frontend(self, temperature):
		_mrbeam_plugin_implementation._plugin_manager.send_plugin_message("mrbeam", dict(status=dict(laser_temperature=temperature)))