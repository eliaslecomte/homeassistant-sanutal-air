# Sanutal Air for Home Assistant

Local control and device feedback for Sanutal AIR ventilation units. Version 0.1.0
exposes a **Ventilation position** selector with options **1–4**. It polls the unit
every 30 seconds and reads back its position after a command. No cloud account or
Android app is required.

This is an initial custom integration, not an official Sanutal product or a HACS
default repository. It supports the HTML interface documented in
[protocol research](docs/implementation-plan.md). Other firmware variants may need
additional parser support.

## Install from Git

1. Clone or download this repository.
2. Copy the entire `custom_components/sanutal_air` directory into
   `<your Home Assistant config directory>/custom_components/sanutal_air`.
   The resulting path must contain `manifest.json` directly inside `sanutal_air`.
3. Restart Home Assistant.
4. Open **Settings → Devices & services** and configure the discovered Sanutal Air,
   or choose **Add integration → Sanutal Air** and enter its IP address or hostname.
   Enter the host without `http://` or a path; the default port is 80.

For upgrades, replace that integration directory and restart. Keep a copy of the
previous version for rollback. To remove it, delete its integration entry, remove
the directory, and restart.

HACS custom-repository installation can use this GitHub repository with category
**Integration** once the code is pushed. HACS default-list submission is a later step.

## Use

Select a position from the entity's dropdown, or call:

```yaml
action: select.select_option
target:
  entity_id: select.sanutal_air_ventilation_position
data:
  option: "3"
```

Check the actual entity ID in your installation. The state represents the device's
selected position, not measured RPM or airflow. Positions 1–3 have configurable
percentages; position 4 corresponds to configured design flow. There is no off
control. Installer settings, scheduling, filters and frost sensors are outside
this release's scope.

The integration does not change existing helpers, shell commands, or automations.
Migrate their actions to this selector after verifying operation, and use its state
for device feedback. Avoid automations that repeatedly overwrite each other's
commands. A command that is not reflected after bounded readback raises an error
and retains the observed state. Failed commands are never automatically replayed.

## Discovery and address changes

The unit observed during development advertises an ESP32 HTTP service with a
Sanutal hostname. Discovery verifies that hostname and the actual Sanutal page;
other ESP32 devices are rejected. Multicast must reach the Home Assistant network.
If discovery is absent, use manual setup.

No stable hardware identifier is exposed by the inspected interface. Entity IDs
are tied to the configuration entry, and addresses are never automatically migrated.
Use the entry's **Reconfigure** menu to change host/port while preserving entity IDs.
A DHCP reservation is recommended. Duplicate detection compares hosts and resolved
addresses at setup; it cannot identify arbitrary aliases after network changes.

Only plain local HTTP is implemented. The unit must be reachable from Home Assistant.
Do not expose this unauthenticated device interface to the internet.

## Troubleshooting

- **Cannot connect:** verify the host and port from the Home Assistant network.
- **Unsupported page:** the page must identify Sanutal and provide exactly one
  selected-position state script. Report firmware differences with a sanitized
  sample; do not send installer passwords or full private configuration.
- **Unavailable:** connection or parsing failed. Polling recovers automatically
  after valid responses resume.
- **Requested position does not stick:** check the unit's schedule, wired controls,
  and Home Assistant automations for competing commands.

## Development and validation

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check custom_components tests
.venv/bin/ruff format --check custom_components tests
.venv/bin/pytest -q
```

The pinned test harness uses Home Assistant 2026.10.0b4. The configured compatibility
floor is 2026.3.0; earlier versions and the minimum version have not yet been tested.
The 27 automated tests pass, along with Ruff and direct hassfest validation.
Tests cover HTML parsing, HTTP requests, setup/discovery, duplicates, reconfiguration,
entity control, availability recovery, and unloading. CI also runs hassfest.
A live test on 2026-10-07 read initial position 3, successfully selected and read back
positions 1, 2, 3, and 4, then restored and confirmed position 3.
Actual installation/restart and discovery on the user's Home Assistant remain
release validation steps; local tests do not establish those outcomes.

See [implementation plan](docs/implementation-plan.md) and
[Android inspection](docs/android-inspection.md) for protocol evidence and limits.
