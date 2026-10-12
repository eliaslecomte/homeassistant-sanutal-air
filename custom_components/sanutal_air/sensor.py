"""Device clock diagnostics."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from .entity import SanutalEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SanutalClock(entry, field) for field in ("clock", "day")])


class SanutalClock(SanutalEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, field):
        super().__init__(entry)
        self.field = field
        self._attr_unique_id = f"{entry.entry_id}_{field}"
        self._attr_translation_key = field
        self._attr_icon = "mdi:clock-outline" if field == "clock" else "mdi:calendar-week"

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def native_value(self):
        return getattr(self.coordinator.data, self.field)
