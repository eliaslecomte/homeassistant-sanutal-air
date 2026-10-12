"""Small, local-only Sanutal HTTP protocol client."""

import asyncio
import re
from dataclasses import dataclass
from html.parser import HTMLParser

import aiohttp
from yarl import URL

MAX_RESPONSE = 256 * 1024
# Only standalone assignment scripts are state. Never inspect click-handler bodies.
ASSIGNMENT = re.compile(
    r"""\s*document\s*\.\s*getElementById\s*\(\s*["']B([1-4])["']\s*\)"""
    r"""\s*\.\s*style\s*\.\s*(backgroundColor|color)\s*=\s*["'](#[0-9a-fA-F]{6})["']\s*;?\s*"""
)


class SanutalError(Exception):
    """Communication failed."""


class InvalidResponse(SanutalError):
    """Device returned unsupported or ambiguous state."""


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.text = []
        self.buttons = set()
        self.script = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.script = []
        if tag == "button":
            self.buttons.add(dict(attrs).get("id"))

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)
        else:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.scripts.append("".join(self.script))
            self.script = None


def parse_position(html: str) -> str:
    """Read exactly one selected button from the server's state scripts."""
    page = _Page()
    page.feed(html)
    if "Sanutal Ventilation" not in " ".join(page.text) or not {"B1", "B2", "B3", "B4"}.issubset(
        page.buttons
    ):
        raise InvalidResponse("Not a supported Sanutal page")
    selected = []
    for script in page.scripts:
        matches = list(ASSIGNMENT.finditer(script))
        if not matches or ASSIGNMENT.sub("", script).strip():
            continue
        for match in matches:
            position, prop, color = match.groups()
            if prop == "backgroundColor" and color.lower() == "#ffffff":
                selected.append(position)
    if len(selected) != 1:
        raise InvalidResponse("Missing or ambiguous selected position")
    return selected[0]


@dataclass(frozen=True)
class SanutalState:
    """Confirmed state; unsupported settings remain unavailable."""

    position: str
    percentages: tuple[int | None, ...] = (None, None, None)
    timer_enabled: bool | None = None
    frost_active: bool | None = None
    filter_reset: bool | None = None
    clock: str | None = None
    day: int | None = None


SETTING = re.compile(
    r"""\s*document\s*\.\s*getElementById\s*\(\s*["'](R[1-3]|C1)["']\s*\)"""
    r"""\s*\.\s*(value|checked)\s*=\s*(\d+|true|false)\s*;?\s*"""
)


STATUS = re.compile(
    r"""\s*document\s*\.\s*getElementById\s*\(\s*["'](D2|D3|T5|T6)["']\s*\)"""
    r"""\s*\.\s*(style\s*\.\s*backgroundColor|value)\s*=\s*(?:["']([^"']*)["']|(\d+))\s*;?\s*"""
)


def parse_state(html: str) -> SanutalState:
    """Parse standalone server assignments, never event handlers."""
    position = parse_position(html)
    page = _Page()
    page.feed(html)
    values = {}
    for script in page.scripts:
        match = SETTING.fullmatch(script)
        if not match:
            continue
        field, prop, value = match.groups()
        if field in values:
            raise InvalidResponse("Duplicate configuration state")
        if field == "C1" and prop == "checked" and value in ("true", "false"):
            values[field] = value == "true"
        elif field.startswith("R") and prop == "value" and value.isdecimal():
            number = int(value)
            if not 1 <= number <= 99:
                raise InvalidResponse("Invalid position percentage")
            values[field] = number
    status = {}
    for script in page.scripts:
        match = STATUS.fullmatch(script)
        if not match:
            continue
        field, prop, quoted, number = match.groups()
        if field in status:
            raise InvalidResponse("Duplicate diagnostic state")
        value = quoted if quoted is not None else number
        status[field] = None
        if field in ("D2", "D3") and prop.replace(" ", "") == "style.backgroundColor":
            status[field] = {"#ffffff": False, "#002b53": True}.get(value.lower())
        elif (
            field == "T5" and prop == "value" and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value)
        ):
            status[field] = value
        elif field == "T6" and prop == "value" and value in tuple(str(n) for n in range(1, 8)):
            status[field] = int(value)
    return SanutalState(
        position,
        tuple(values.get(f"R{n}") for n in range(1, 4)),
        values.get("C1"),
        status.get("D2"),
        status.get("D3"),
        status.get("T5"),
        status.get("T6"),
    )


class SanutalClient:
    """Serialize all traffic, including command/readback transactions."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int = 80):
        self.session = session
        self.url = URL.build(scheme="http", host=host, port=port)
        self.lock = asyncio.Lock()

    async def _request(self, method: str, path: str, data: str | None = None) -> str:
        try:
            async with self.session.request(
                method,
                self.url.with_path(path),
                data=data,
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=False,
            ) as response:
                if not 200 <= response.status < 300:
                    raise SanutalError(f"Device returned HTTP {response.status}")
                body = bytearray()
                async for chunk in response.content.iter_chunked(8192):
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE:
                        raise InvalidResponse("Device response is too large")
                return body.decode("utf-8", errors="replace")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SanutalError("Cannot communicate with device") from err

    async def read_position(self) -> str:
        async with self.lock:
            return parse_position(await self._request("GET", "/"))

    async def set_position(self, position: str) -> str:
        if position not in ("1", "2", "3", "4"):
            raise ValueError("Position must be 1, 2, 3, or 4")
        async with self.lock:
            await self._request("POST", f"/upload/B{position}", f"B{position}")
            # Retry reads, never commands: a timeout may follow an applied command.
            for attempt in range(3):
                await asyncio.sleep(0.3 if attempt == 0 else 0.5)
                observed = parse_position(await self._request("GET", "/"))
                if observed == position:
                    break
            return observed

    async def read_state(self) -> SanutalState:
        async with self.lock:
            return parse_state(await self._request("GET", "/"))

    async def set_setting(self, field: str, value: int | bool | str) -> SanutalState:
        if field == "T5":
            if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
                raise ValueError("Clock must be HH:MM")
            payload = value
        elif field == "T6":
            if type(value) is not int or not 1 <= value <= 7:
                raise ValueError("Day must be an integer from 1 to 7")
            payload = str(value)
        elif field == "C1":
            if not isinstance(value, bool):
                raise ValueError("Timer must be a boolean")
            payload = str(int(value))
        elif field in ("R1", "R2", "R3"):
            if type(value) is not int or not 1 <= value <= 99:
                raise ValueError("Percentage must be an integer from 1 to 99")
            payload = str(value)
        else:
            raise ValueError("Unsupported setting")
        async with self.lock:
            await self._request("POST", f"/upload/{field}{payload}", field)
            for attempt in range(3):
                await asyncio.sleep(0.3 if attempt == 0 else 0.5)
                state = parse_state(await self._request("GET", "/"))
                if field in ("T5", "T6", "C1"):
                    observed = getattr(
                        state, {"T5": "clock", "T6": "day", "C1": "timer_enabled"}[field]
                    )
                else:
                    observed = state.percentages[int(field[1]) - 1]
                if observed == value:
                    return state
            raise SanutalError("Device did not confirm the requested setting")
