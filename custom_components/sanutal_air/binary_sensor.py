"""Read-only device status indicators."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import SanutalEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [SanutalIndicator(entry, field) for field in ("frost_active", "filter_reset")]
    )


class SanutalIndicator(SanutalEntity, BinarySensorEntity):
    def __init__(self, entry, field):
        super().__init__(entry)
        self.field = field
        self._attr_unique_id = f"{entry.entry_id}_{field}"
        self._attr_translation_key = field
        self._attr_icon = "mdi:snowflake" if field == "frost_active" else "mdi:air-filter"

    @property
    def available(self):
        return super().available and self.is_on is not None

    @property
    def is_on(self):
        return getattr(self.coordinator.data, self.field)
