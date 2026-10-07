"""Observed ventilation position selector."""

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SanutalSelect(entry)])


class SanutalSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "position"
    _attr_options = ["1", "2", "3", "4"]
    _attr_icon = "mdi:fan"

    def __init__(self, entry):
        super().__init__(entry.runtime_data)
        self._attr_unique_id = f"{entry.entry_id}_position"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sanutal Air",
            manufacturer="Sanutal",
            model="Air",
            configuration_url=str(self.coordinator.client.url),
        )

    @property
    def current_option(self):
        return self.coordinator.data

    async def async_select_option(self, option):
        await self.coordinator.async_select(option)
