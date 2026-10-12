"""Shared Sanutal device entity."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class SanutalEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry):
        super().__init__(entry.runtime_data)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sanutal Air",
            manufacturer="Sanutal",
            model="Air",
            configuration_url=str(self.coordinator.client.url),
        )
