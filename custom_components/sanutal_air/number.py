"""Configured ventilation percentages."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory

from .entity import SanutalEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SanutalPercentage(entry, n) for n in range(1, 4)])


class SanutalPercentage(SanutalEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 99
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, position):
        super().__init__(entry)
        self.position = position
        self._attr_unique_id = f"{entry.entry_id}_position_{position}_percentage"
        self._attr_translation_key = f"position_{position}_percentage"

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def native_value(self):
        return self.coordinator.data.percentages[self.position - 1]

    async def async_set_native_value(self, value):
        if not float(value).is_integer():
            raise ValueError("Percentage must be a whole number")
        await self.coordinator.async_set_setting(f"R{self.position}", int(value))
