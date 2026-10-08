# Changelog

## 0.1.1 — 2026-10-08

- Replace the square white background with transparent official Sanutal sphere icons.
- Add the official white Sanutal wordmark for dark themes.
- Preserve SVG sources and document their origin.


## 0.1.0 — 2026-10-08

Initial release of the Sanutal Air Home Assistant integration.

- Local HTTP control of ventilation positions 1–4.
- Device state feedback every 30 seconds and readback after commands.
- Manual IP/hostname setup and validated Zeroconf discovery.
- Connection reconfiguration preserving entity IDs.
- Availability recovery after communication failures.
- HACS custom-repository installation and bundled Sanutal logo.

Validation: 27 automated tests, Ruff, hassfest, and HACS validation. Live device
commands confirmed all four positions and restored the original position. Installed
successfully through Zeroconf on Home Assistant Core 2026.10.0, with matching state
readback and no Sanutal runtime errors in the inspected logs.

The supported interface is the device-hosted HTML page. Selected position is not
measured RPM or airflow. Scheduling and installer settings are outside this release.
Automatic IP migration is unavailable because the interface exposes no verified
stable hardware ID; use Reconfigure when the address changes.
