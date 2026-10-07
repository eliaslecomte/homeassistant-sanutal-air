"""Device polling and confirmed control."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SanutalError
from .const import DOMAIN


class SanutalCoordinator(DataUpdateCoordinator[str]):
    def __init__(self, hass, entry, client):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=30),
        )
        self.client = client
        self.command_lock = asyncio.Lock()

    async def _async_update_data(self):
        async with self.command_lock:
            try:
                return await self.client.read_position()
            except SanutalError as err:
                raise UpdateFailed(str(err)) from err

    async def async_select(self, position):
        async with self.command_lock:
            try:
                observed = await self.client.set_position(position)
            except SanutalError as err:
                self.async_set_update_error(UpdateFailed(str(err)))
                raise HomeAssistantError(str(err)) from err
            self.async_set_updated_data(observed)
            if observed != position:
                raise HomeAssistantError(
                    f"Device reports position {observed}; requested {position}. "
                    "An external control may be overriding it."
                )
