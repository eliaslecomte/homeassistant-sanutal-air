"""Sanutal Air integration."""

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SanutalClient
from .coordinator import SanutalCoordinator

PLATFORMS = [Platform.SELECT]


async def async_setup_entry(hass, entry):
    client = SanutalClient(async_get_clientsession(hass), entry.data["host"], entry.data["port"])
    coordinator = SanutalCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
