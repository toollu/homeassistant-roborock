"""Support for Roborock sensors."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time
from typing import Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription, SensorDeviceClass, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    AREA_SQUARE_METERS, TIME_SECONDS
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util, slugify

from . import DOMAIN, RoborockDataUpdateCoordinator
from .api.containers import CleanRecordField, StatusField, CleanSummaryField, ConsumableField, DNDTimerField
from .api.typing import RoborockDeviceInfo, RoborockDevicePropField
from .device import RoborockCoordinatedEntity, parse_datetime_time

_LOGGER = logging.getLogger(__name__)

ATTR_ACTUAL_SPEED = "actual_speed"
ATTR_AIR_QUALITY = "air_quality"
ATTR_TVOC = "tvoc"
ATTR_AQI = "aqi"
ATTR_BATTERY = "battery"
ATTR_CARBON_DIOXIDE = "co2"
ATTR_CHARGING = "charging"
ATTR_CONTROL_SPEED = "control_speed"
ATTR_DISPLAY_CLOCK = "display_clock"
ATTR_FAVORITE_SPEED = "favorite_speed"
ATTR_FILTER_LIFE_REMAINING = "filter_life_remaining"
ATTR_FILTER_HOURS_USED = "filter_hours_used"
ATTR_FILTER_LEFT_TIME = "filter_left_time"
ATTR_DUST_FILTER_LIFE_REMAINING = "dust_filter_life_remaining"
ATTR_DUST_FILTER_LIFE_REMAINING_DAYS = "dust_filter_life_remaining_days"
ATTR_UPPER_FILTER_LIFE_REMAINING = "upper_filter_life_remaining"
ATTR_UPPER_FILTER_LIFE_REMAINING_DAYS = "upper_filter_life_remaining_days"
ATTR_FILTER_USE = "filter_use"
ATTR_HUMIDITY = "humidity"
ATTR_ILLUMINANCE = "illuminance"
ATTR_ILLUMINANCE_LUX = "illuminance_lux"
ATTR_LOAD_POWER = "load_power"
ATTR_MOTOR2_SPEED = "motor2_speed"
ATTR_MOTOR_SPEED = "motor_speed"
ATTR_NIGHT_MODE = "night_mode"
ATTR_NIGHT_TIME_BEGIN = "night_time_begin"
ATTR_NIGHT_TIME_END = "night_time_end"
ATTR_PM10 = "pm10_density"
ATTR_PM25 = "pm25"
ATTR_PM25_2 = "pm25_2"
ATTR_POWER = "power"
ATTR_PRESSURE = "pressure"
ATTR_PURIFY_VOLUME = "purify_volume"
ATTR_SENSOR_STATE = "sensor_state"
ATTR_USE_TIME = "use_time"
ATTR_WATER_LEVEL = "water_level"
ATTR_DND_START = "start"
ATTR_DND_END = "end"
ATTR_LAST_CLEAN_TIME = "duration"
ATTR_LAST_CLEAN_AREA = "area"
ATTR_STATUS_CLEAN_TIME = "clean_time"
ATTR_STATUS_CLEAN_AREA = "clean_area"
ATTR_LAST_CLEAN_START = "start"
ATTR_LAST_CLEAN_END = "end"
ATTR_CLEAN_HISTORY_TOTAL_DURATION = "total_duration"
ATTR_CLEAN_HISTORY_TOTAL_AREA = "total_area"
ATTR_CLEAN_HISTORY_COUNT = "count"
ATTR_CLEAN_HISTORY_DUST_COLLECTION_COUNT = "dust_collection_count"
ATTR_CONSUMABLE_STATUS_MAIN_BRUSH_LEFT = "main_brush_left"
ATTR_CONSUMABLE_STATUS_SIDE_BRUSH_LEFT = "side_brush_left"
ATTR_CONSUMABLE_STATUS_FILTER_LEFT = "filter_left"
ATTR_CONSUMABLE_STATUS_SENSOR_DIRTY_LEFT = "sensor_dirty_left"


@dataclass
class RoborockSensorDescription(SensorEntityDescription):
    """A class that describes sensor entities."""
    attributes: tuple = ()
    parent_key: str = None
    keys: list[str] = None
    value: Callable = None


VACUUM_SENSORS = {
    f"dnd_{ATTR_DND_START}": RoborockSensorDescription(
        key=ATTR_DND_START,
        keys=[DNDTimerField.START_HOUR, DNDTimerField.START_MINUTE],
        value=lambda values: parse_datetime_time(time(hour=values[0], minute=values[1])),
        icon="mdi:minus-circle-off",
        name="DnD start",
        device_class=SensorDeviceClass.TIMESTAMP,
        parent_key=RoborockDevicePropField.DND_TIMER,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"dnd_{ATTR_DND_END}": RoborockSensorDescription(
        key=ATTR_DND_END,
        keys=[DNDTimerField.END_HOUR, DNDTimerField.END_MINUTE],
        value=lambda values: parse_datetime_time(time(hour=values[0], minute=values[1])),
        icon="mdi:minus-circle-off",
        name="DnD end",
        device_class=SensorDeviceClass.TIMESTAMP,
        parent_key=RoborockDevicePropField.DND_TIMER,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"last_clean_{ATTR_LAST_CLEAN_START}": RoborockSensorDescription(
        key=CleanRecordField.BEGIN,
        icon="mdi:clock-time-twelve",
        name="Last clean start",
        device_class=SensorDeviceClass.TIMESTAMP,
        parent_key=RoborockDevicePropField.LAST_CLEAN_RECORD,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"last_clean_{ATTR_LAST_CLEAN_END}": RoborockSensorDescription(
        key=CleanRecordField.END,
        icon="mdi:clock-time-twelve",
        device_class=SensorDeviceClass.TIMESTAMP,
        parent_key=RoborockDevicePropField.LAST_CLEAN_RECORD,
        name="Last clean end",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"last_clean_{ATTR_LAST_CLEAN_TIME}": RoborockSensorDescription(
        native_unit_of_measurement=TIME_SECONDS,
        key=CleanRecordField.DURATION,
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        parent_key=RoborockDevicePropField.LAST_CLEAN_RECORD,
        name="Last clean duration",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"last_clean_{ATTR_LAST_CLEAN_AREA}": RoborockSensorDescription(
        native_unit_of_measurement=AREA_SQUARE_METERS,
        key=CleanRecordField.AREA,
        value=lambda value: value / 1000000,
        icon="mdi:texture-box",
        parent_key=RoborockDevicePropField.LAST_CLEAN_RECORD,
        name="Last clean area",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"current_{ATTR_STATUS_CLEAN_TIME}": RoborockSensorDescription(
        native_unit_of_measurement=TIME_SECONDS,
        key=StatusField.CLEAN_TIME,
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        parent_key=RoborockDevicePropField.STATUS,
        name="Current clean duration",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"current_{ATTR_LAST_CLEAN_AREA}": RoborockSensorDescription(
        native_unit_of_measurement=AREA_SQUARE_METERS,
        key=StatusField.CLEAN_AREA,
        value=lambda value: value / 1000000,
        icon="mdi:texture-box",
        parent_key=RoborockDevicePropField.STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Current clean area",
    ),
    f"clean_history_{ATTR_CLEAN_HISTORY_TOTAL_DURATION}": RoborockSensorDescription(
        native_unit_of_measurement=TIME_SECONDS,
        device_class=SensorDeviceClass.DURATION,
        key=CleanSummaryField.CLEAN_TIME,
        icon="mdi:timer-sand",
        parent_key=RoborockDevicePropField.CLEAN_SUMMARY,
        name="Total duration",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"clean_history_{ATTR_CLEAN_HISTORY_TOTAL_AREA}": RoborockSensorDescription(
        native_unit_of_measurement=AREA_SQUARE_METERS,
        key=CleanSummaryField.CLEAN_AREA,
        value=lambda value: value / 1000000,
        icon="mdi:texture-box",
        parent_key=RoborockDevicePropField.CLEAN_SUMMARY,
        name="Total clean area",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"clean_history_{ATTR_CLEAN_HISTORY_COUNT}": RoborockSensorDescription(
        native_unit_of_measurement="",
        key=CleanSummaryField.CLEAN_COUNT,
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        parent_key=RoborockDevicePropField.CLEAN_SUMMARY,
        name="Total clean count",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"clean_history_{ATTR_CLEAN_HISTORY_DUST_COLLECTION_COUNT}": RoborockSensorDescription(
        native_unit_of_measurement="",
        key=CleanSummaryField.CLEAN_COUNT,
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        parent_key=RoborockDevicePropField.CLEAN_SUMMARY,
        name="Total dust collection count",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"consumable_{ATTR_CONSUMABLE_STATUS_MAIN_BRUSH_LEFT}": RoborockSensorDescription(
        native_unit_of_measurement=TIME_SECONDS,
        key=ConsumableField.MAIN_BRUSH_WORK_TIME,
        icon="mdi:brush",
        device_class=SensorDeviceClass.DURATION,
        parent_key=RoborockDevicePropField.CONSUMABLE,
        name="Main brush left",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"consumable_{ATTR_CONSUMABLE_STATUS_SIDE_BRUSH_LEFT}": RoborockSensorDescription(
        native_unit_of_measurement=TIME_SECONDS,
        key=ConsumableField.SIDE_BRUSH_WORK_TIME,
        icon="mdi:brush",
        device_class=SensorDeviceClass.DURATION,
        parent_key=RoborockDevicePropField.CONSUMABLE,
        name="Side brush left",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"consumable_{ATTR_CONSUMABLE_STATUS_FILTER_LEFT}": RoborockSensorDescription(
        native_unit_of_measurement=TIME_SECONDS,
        key=ConsumableField.FILTER_WORK_TIME,
        icon="mdi:air-filter",
        device_class=SensorDeviceClass.DURATION,
        parent_key=RoborockDevicePropField.CONSUMABLE,
        name="Filter left",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    f"consumable_{ATTR_CONSUMABLE_STATUS_SENSOR_DIRTY_LEFT}": RoborockSensorDescription(
        native_unit_of_measurement=TIME_SECONDS,
        key=ConsumableField.SENSOR_DIRTY_TIME,
        icon="mdi:eye-outline",
        device_class=SensorDeviceClass.DURATION,
        parent_key=RoborockDevicePropField.CONSUMABLE,
        name="Sensor dirty left",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Roborock vacuum sensors."""
    entities = []
    coordinator: RoborockDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    for device_id, device_info in coordinator.api.device_map.items():
        unique_id = slugify(device_id)
        for sensor, description in VACUUM_SENSORS.items():
            parent_key_data = getattr(coordinator.data.get(device_id), description.parent_key)
            if not parent_key_data:
                _LOGGER.debug(
                    "It seems the %s does not support the %s as the initial value is None",
                    device_info.product.model,
                    description.key,
                )
                continue
            entities.append(
                RoborockSensor(
                    f"{sensor}_{unique_id}",
                    device_info,
                    coordinator,
                    description,
                )
            )

    async_add_entities(entities)


class RoborockSensor(RoborockCoordinatedEntity, SensorEntity):
    """Representation of a Roborock sensor."""

    entity_description: RoborockSensorDescription

    def __init__(self, unique_id: str, device_info: RoborockDeviceInfo, coordinator: RoborockDataUpdateCoordinator,
                 description: RoborockSensorDescription):
        """Initialize the entity."""
        SensorEntity.__init__(self)
        RoborockCoordinatedEntity.__init__(self, device_info, coordinator, unique_id)
        self.entity_description = description
        self._attr_native_value = self._determine_native_value()
        self._attr_extra_state_attributes = self._extract_attributes(coordinator.data.get(self._device_id))

    @callback
    def _extract_attributes(self, data):
        """Return state attributes with valid values."""
        value = None
        return {
            attr: value
            for attr in self.entity_description.attributes
            if hasattr(data, attr)
        }

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
        native_value = self._determine_native_value()
        # Sometimes (quite rarely) the device returns None as the sensor value so we
        # check that the value: before updating the state.
        if native_value:
            data = self.coordinator.data.get(self._device_id)
            self._attr_native_value = native_value
            self._attr_extra_state_attributes = self._extract_attributes(data)
            self.async_write_ha_state()

    def _determine_native_value(self):
        """Determine native value."""
        data = self.coordinator.data.get(self._device_id)
        if self.entity_description.parent_key:
            data = getattr(data, self.entity_description.parent_key)

        if self.entity_description.keys:
            native_value = [
                getattr(data, key) for key in self.entity_description.keys
            ]
        else:
            native_value = getattr(data, self.entity_description.key)

        if self.entity_description.value and native_value:
            native_value = self.entity_description.value(native_value)

        if (
                self.device_class == SensorDeviceClass.TIMESTAMP
                and native_value
                and (native_datetime := datetime.fromtimestamp(native_value))
        ):
            return native_datetime.astimezone(dt_util.UTC)

        return native_value
