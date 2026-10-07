"""Manual setup, conservative Zeroconf discovery, and reconfiguration."""

import asyncio
import ipaddress
import re
import socket

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InvalidResponse, SanutalClient, SanutalError
from .const import DOMAIN


def normalize_host(value):
    host = value.strip().lower().rstrip(".")
    try:
        return str(ipaddress.ip_address(host.strip("[]")))
    except ValueError:
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host):
            raise ValueError("Enter an IP address or hostname, without a URL") from None
        return host


class SanutalFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, data):
        data = {"host": normalize_host(data["host"]), "port": data["port"]}
        await SanutalClient(async_get_clientsession(self.hass), **data).read_position()
        # Resolve aliases for duplicate detection only, not as hardware identity.
        try:
            async with asyncio.timeout(5):
                addresses = await asyncio.get_running_loop().getaddrinfo(
                    data["host"], data["port"], type=socket.SOCK_STREAM
                )
            data["addresses"] = sorted({item[4][0] for item in addresses})
        except (OSError, TimeoutError):
            data["addresses"] = []
        return data

    def _check_duplicates(self, data):
        for entry in self._async_current_entries():
            if entry.entry_id == self.context.get("entry_id"):
                continue
            if entry.data["port"] != data["port"]:
                continue
            if entry.data["host"] == data["host"] or set(
                entry.data.get("addresses", [])
            ).intersection(data.get("addresses", [])):
                return True
        return False

    async def _form(self, step, user_input, defaults=None):
        errors = {}
        if user_input is not None:
            try:
                data = await self._validate(user_input)
            except ValueError:
                errors["host"] = "invalid_host"
            except InvalidResponse:
                errors["base"] = "unsupported_device"
            except SanutalError:
                errors["base"] = "cannot_connect"
            else:
                if self._check_duplicates(data):
                    return self.async_abort(reason="already_configured")
                # Endpoint unique_id coalesces concurrent setup flows; not a hardware ID.
                await self.async_set_unique_id(f"{data['host']}:{data['port']}")
                if step == "reconfigure":
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(),
                        data_updates=data,
                        unique_id=f"{data['host']}:{data['port']}",
                    )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Sanutal Air", data=data)
        if step == "confirm":
            return self.async_show_form(
                step_id="confirm",
                errors=errors,
                data_schema=vol.Schema({}),
                description_placeholders={"host": self._discovered["host"]},
            )
        values = user_input or defaults or {}
        return self.async_show_form(
            step_id=step,
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("host", default=values.get("host", "")): str,
                    vol.Required("port", default=values.get("port", 80)): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
        )

    async def async_step_user(self, user_input=None):
        return await self._form("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._form("reconfigure", user_input, self._get_reconfigure_entry().data)

    async def async_step_zeroconf(self, discovery_info):
        if not re.fullmatch(r"sanutal[a-z0-9-]*\.local\.?", discovery_info.hostname.lower()):
            return self.async_abort(reason="unsupported_device")
        try:
            self._discovered = await self._validate(
                {
                    "host": discovery_info.host,
                    "port": discovery_info.port,
                }
            )
        except (SanutalError, ValueError):
            return self.async_abort(reason="unsupported_device")
        if self._check_duplicates(self._discovered):
            return self.async_abort(reason="already_configured")
        await self.async_set_unique_id(f"{self._discovered['host']}:{self._discovered['port']}")
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": "Sanutal Air"}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        if user_input is not None:
            # Revalidate at confirmation; a pending discovery may be stale.
            return await self._form("confirm", self._discovered)
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"host": self._discovered["host"]},
        )
