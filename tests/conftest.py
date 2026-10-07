import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


def page(position="3"):
    buttons = "".join(f'<button id="B{n}">{n}</button>' for n in range(1, 5))
    handlers = "".join(
        f'document.getElementById("B{n}").style.backgroundColor="#ffffff";' for n in range(1, 5)
    )
    state = f'document.getElementById("B{position}").style.backgroundColor="#ffffff";'
    return (
        f"<h1>Sanutal Ventilation</h1>{buttons}"
        f"<script>function upload(){{{handlers}}}</script><script>{state}</script>"
    )
