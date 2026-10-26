"""Constants for smart_tag."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "smart_tag"
ATTRIBUTION = "Data provided by https://smart-tag.net/"

CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"

CONF_MORNING_START = "morning_start"
CONF_MORNING_END = "morning_end"
CONF_AFTERNOON_START = "afternoon_start"
CONF_AFTERNOON_END = "afternoon_end"
CONF_WEEKDAYS_ONLY = "weekdays_only"
CONF_APPROACH_DISTANCE = "approach_distance"

DEFAULT_MORNING_START = "06:30:00"
DEFAULT_MORNING_END = "08:45:00"
DEFAULT_AFTERNOON_START = "14:30:00"
DEFAULT_AFTERNOON_END = "17:00:00"
DEFAULT_WEEKDAYS_ONLY = True
DEFAULT_APPROACH_DISTANCE = 1500  # meters

STATUS_ON_BUS = "on_bus"
STATUS_DROPPED_OFF = "dropped_off"
STATUS_NO_RIDE_TODAY = "no_ride_today"
