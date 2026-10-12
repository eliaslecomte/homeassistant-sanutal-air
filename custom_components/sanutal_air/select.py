"""Observed ventilation position selector."""

from homeassistant.components.select import SelectEntity

from .entity import SanutalEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SanutalSelect(entry)])


class SanutalSelect(SanutalEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "position"
    _attr_options = ["1", "2", "3", "4"]
    _attr_icon = "mdi:fan"

    def __init__(self, entry):
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_position"

    @property
    def current_option(self):
        return self.coordinator.data.position

    async def async_select_option(self, option):
        await self.coordinator.async_select(option)
