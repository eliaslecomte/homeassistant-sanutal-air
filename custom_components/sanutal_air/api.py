"""Small, local-only Sanutal HTTP protocol client."""

import asyncio
import re
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
