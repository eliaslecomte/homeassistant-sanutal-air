from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sanutal_air.api import InvalidResponse, SanutalError
from custom_components.sanutal_air.const import DOMAIN


@pytest.fixture
async def client():
    with patch(
        "custom_components.sanutal_air.api.SanutalClient.read_position", return_value="3"
    ) as read:
        yield read


async def test_manual_and_duplicate(hass, client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    with patch("custom_components.sanutal_air.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "127.0.0.1", "port": 80}
        )
        assert result["type"] == "create_entry"
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={"host": "127.0.0.1", "port": 80}
        )
        assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "error,expected",
    [(SanutalError(), "cannot_connect"), (InvalidResponse(), "unsupported_device")],
)
async def test_setup_errors(hass, client, error, expected):
    client.side_effect = error
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={"host": "127.0.0.1", "port": 80}
    )
    assert result["errors"]["base"] == expected


async def test_invalid_host(hass, client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={"host": "http://127.0.0.1/path", "port": 80}
    )
    assert result["errors"]["host"] == "invalid_host"
    client.assert_not_called()


async def test_discovery(hass, client):
    info = SimpleNamespace(hostname="SANUTAL27.local.", host="127.0.0.1", port=80)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info
    )
    assert result["step_id"] == "confirm"
    with patch("custom_components.sanutal_air.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] == "create_entry"
    info.hostname = "other.local."
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info
    )
    assert result["reason"] == "unsupported_device"


async def test_entity_control_recovery_unload(hass, client):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "127.0.0.1", "port": 80})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = "select.sanutal_air_ventilation_position"
    assert hass.states.get(entity_id).state == "3"
    with patch.object(entry.runtime_data.client, "set_position", AsyncMock(return_value="2")):
        await hass.services.async_call(
            "select", "select_option", {"entity_id": entity_id, "option": "2"}, blocking=True
        )
    assert hass.states.get(entity_id).state == "2"
    client.side_effect = SanutalError("offline")
    await entry.runtime_data.async_refresh()
    assert hass.states.get(entity_id).state == "unavailable"
    client.side_effect = None
    client.return_value = "4"
    await entry.runtime_data.async_refresh()
    assert hass.states.get(entity_id).state == "4"
    with patch.object(entry.runtime_data.client, "set_position", AsyncMock(return_value="1")):
        with pytest.raises(HomeAssistantError):
            await entry.runtime_data.async_select("3")
    assert hass.states.get(entity_id).state == "1"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_reconfigure(hass, client):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="127.0.0.1:80", data={"host": "127.0.0.1", "port": 80}
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    with patch("custom_components.sanutal_air.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "127.0.0.2", "port": 80}
        )
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "127.0.0.2"


async def test_discovered_duplicate_of_manual(hass, client):
    entry = MockConfigEntry(
        domain=DOMAIN, data={"host": "sanutal.local", "port": 80, "addresses": ["127.0.0.1"]}
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=SimpleNamespace(hostname="SANUTAL27.local.", host="127.0.0.1", port=80),
    )
    assert result["reason"] == "already_configured"


async def test_initial_connection_failure(hass, client):
    from homeassistant.config_entries import ConfigEntryState

    client.side_effect = SanutalError("offline")
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "127.0.0.1", "port": 80})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_failed_command_marks_unavailable(hass, client):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "127.0.0.1", "port": 80})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    with patch.object(
        entry.runtime_data.client, "set_position", side_effect=SanutalError("offline")
    ):
        with pytest.raises(HomeAssistantError):
            await entry.runtime_data.async_select("2")
    assert not entry.runtime_data.last_update_success


async def test_discovery_confirmation_offline(hass, client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=SimpleNamespace(hostname="SANUTAL27.local.", host="127.0.0.1", port=80),
    )
    client.side_effect = SanutalError("offline")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "confirm"
    assert result["errors"] == {"base": "cannot_connect"}
    assert result["description_placeholders"]["host"] == "127.0.0.1"
