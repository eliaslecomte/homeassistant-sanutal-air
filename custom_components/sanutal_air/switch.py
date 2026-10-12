"""Device timer control."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from .entity import SanutalEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SanutalTimer(entry)])


class SanutalTimer(SanutalEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "timer"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, entry):
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_timer"

    @property
    def available(self):
        return super().available and self.is_on is not None

    @property
    def is_on(self):
        return self.coordinator.data.timer_enabled

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_set_setting("C1", True)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_setting("C1", False)
