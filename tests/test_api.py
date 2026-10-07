from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aiohttp import web

from custom_components.sanutal_air.api import (
    MAX_RESPONSE,
    InvalidResponse,
    SanutalClient,
    SanutalError,
    parse_position,
)

from .conftest import page


@pytest.mark.parametrize("position", ["1", "2", "3", "4"])
def test_parse(position):
    assert parse_position(page(position)) == position
    assert parse_position(page(position).replace('"', "'").replace("=", " = ")) == position


@pytest.mark.parametrize(
    "html",
    [
        "<html>Other device</html>",
        page().replace("<script>document.", "<script>if (false) document."),
        page() + '<script>document.getElementById("B2").style.backgroundColor="#ffffff";</script>',
        page().replace(
            'B3").style.backgroundColor="#ffffff";', 'B3").style.backgroundColor="#002b53";'
        ),
    ],
)
def test_invalid(html):
    with pytest.raises(InvalidResponse):
        parse_position(html)


async def test_http_transaction(socket_enabled, aiohttp_server):
    requests = []
    position = "1"

    async def handler(request):
        nonlocal position
        body = await request.text()
        requests.append((request.method, request.path, body))
        if request.method == "POST":
            position = body[1:]
            return web.Response(text="OK")
        return web.Response(text=page(position))

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as session:
        client = SanutalClient(session, server.host, server.port)
        assert await client.read_position() == "1"
        assert await client.set_position("4") == "4"
        with pytest.raises(ValueError):
            await client.set_position("0")
    assert requests == [("GET", "/", ""), ("POST", "/upload/B4", "B4"), ("GET", "/", "")]


@pytest.mark.parametrize(
    "status,body,error",
    [
        (500, "error", SanutalError),
        (302, "", SanutalError),
        (200, "x" * (MAX_RESPONSE + 1), InvalidResponse),
        (200, "bad", InvalidResponse),
    ],
    ids=["server_error", "redirect", "oversized", "bad_html"],
)
async def test_http_failure(socket_enabled, aiohttp_server, status, body, error):
    app = web.Application()

    async def handler(request):
        return web.Response(status=status, text=body)

    app.router.add_get("/", handler)
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(error):
            await SanutalClient(session, server.host, server.port).read_position()


async def test_timeout_and_no_replayed_write():
    session = AsyncMock()
    client = SanutalClient(session, "example.local")
    with patch.object(client, "_request", side_effect=SanutalError("timeout")) as request:
        with pytest.raises(SanutalError):
            await client.set_position("2")
        assert request.call_count == 1
    with patch.object(
        client, "_request", side_effect=["OK", page("1"), page("1"), page("1")]
    ) as request:
        assert await client.set_position("2") == "1"
        assert request.call_count == 4


async def test_transport_timeout():
    from unittest.mock import Mock

    session = Mock()
    session.request.side_effect = TimeoutError()
    with pytest.raises(SanutalError, match="Cannot communicate"):
        await SanutalClient(session, "example.local").read_position()


async def test_commands_are_serialized():
    import asyncio

    client = SanutalClient(AsyncMock(), "example.local")
    calls = []
    position = "1"

    async def request(method, path, data=None):
        nonlocal position
        calls.append((method, data))
        await asyncio.sleep(0)
        if method == "POST":
            position = data[1:]
            return "OK"
        return page(position)

    with patch.object(client, "_request", side_effect=request):
        assert await asyncio.gather(client.set_position("2"), client.set_position("4")) == [
            "2",
            "4",
        ]
    assert calls == [("POST", "B2"), ("GET", None), ("POST", "B4"), ("GET", None)]
