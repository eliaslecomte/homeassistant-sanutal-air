"""Device clock configuration."""

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory

from .entity import SanutalEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SanutalClock(entry)])


class SanutalClock(SanutalEntity, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "clock"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, entry):
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_clock"

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def native_value(self):
        value = self.coordinator.data.clock
        return time.fromisoformat(value) if value is not None else None

    async def async_set_value(self, value):
        if value.second or value.microsecond:
            raise ValueError("Device clock supports whole minutes only")
        await self.coordinator.async_set_setting("T5", value.strftime("%H:%M"))
