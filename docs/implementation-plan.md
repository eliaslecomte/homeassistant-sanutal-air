# Sanutal Air: findings and implementation plan

Investigation date: 2026-10-07. Scope: read the selected ventilation position and select positions 1–4. All live investigation was read-only; no control POSTs or Home Assistant configuration changes were made.

## Product and scope

Sanutal AIR is a balanced supply/extract ventilation system with heat recovery. The manufacturer's manual describes four positions, with position 4 representing the configured design flow (100%). Positions 1–3 are configurable. This is a selected operating position, not measured fan RPM or proof of actual airflow. Frost protection and external controls can affect operation.

The app listing describes local Wi-Fi control, schedules, status, and installer settings. These additional features are outside the initial scope.

Sources: [manufacturer manual](https://sanutal.be/uploads/downloads/Handleiding-Sanutal-Air-NL.pdf), [Android app](https://play.google.com/store/apps/details?id=be.sanutal.airventilation).

## Confirmed local protocol

Two successful GET requests to the supplied device returned its HTML interface and selected position 3. No authentication was needed for this read.

| Operation | Request | Evidence |
| --- | --- | --- |
| Read selected position | `GET /` | Live HTML contains server-emitted state scripts |
| Select position N | `POST /upload/BN`, raw body `BN` | Device JavaScript and existing user shell commands; not executed during investigation |

For N=3, the returned state includes:

```javascript
document.getElementById("B3").style.backgroundColor="#ffffff";
document.getElementById("B3").style.color="#002b53";
```

These statements occur in a separate script after the main script defining `upload()`. The main script contains equivalent styling for **all four positions** inside click handlers. A regex over the whole page would therefore return false matches. Parse HTML script boundaries, then recognize only the narrowly defined standalone state assignments. Never execute device JavaScript. Require exactly one unambiguous selected position and expected Sanutal page markers; missing or conflicting state is a protocol error, not a default position.

The live page also exposes R1=10, R2=30, R3=65, labelled POS1/2/3 %. Do not assume 25/50/75% on every installation. The page refreshes itself every 60 seconds. No JSON endpoint was identified; unknown endpoints were not probed.

The upload function uses `XMLHttpRequest.open("POST", path, true)` and `send(clicked_id)`. Match the raw text payload; do not JSON-encode or send multipart data. Response semantics and update latency still need a controlled write/read validation.

The supplied generic shell command has a likely typo: its path uses `speed` but its body always renders `B4`. The intended body is `B{{ speed }}`. Whether current firmware ignores a mismatched body is unverified. `--insecure` has no effect on plain HTTP.

## Discovery

Avahi browsing confirmed the supplied device advertises:

```text
service type: _http._tcp
instance: ESP32-WebServer
hostname: SANUTAL27.local
port: 80
TXT: empty
```

The same device was observed through Ethernet and Wi-Fi. Duplicate discovery must produce one configuration entry. The generic instance name is not a device identifier and is insufficient to identify Sanutal hardware.

Implement Home Assistant Zeroconf discovery for `_http._tcp.local.` with the narrowest supported matcher, followed by hostname-prefix and HTTP fingerprint validation in the config flow. Validate the exact manifest matcher schema against the supported Home Assistant version during implementation. Retain manual IP/hostname entry for networks where multicast does not reach Home Assistant. Discovery from this workstation does not establish multicast visibility from Home Assistant.

No serial number or globally unique device ID was found in the normal page. The hostname suffix is not proven unique. Resolve device identity before promising automatic IP migration: prefer a verified hardware identifier when reliably available, otherwise use config-entry-based entity IDs and host-based duplicate checks, with an explicit reconfigure flow. Do not claim the generic service name or an IP address is a stable hardware ID.

Reference: [Home Assistant manifest and discovery](https://developers.home-assistant.io/docs/creating_integration_manifest/).

## Existing Home Assistant setup

The MCP confirmed five `shell_command.curl_ventilation_speed*` services. During inspection, `input_number.ventilation` was 2 while the device page reported 3. This demonstrates that the helper is not reliable device feedback; the cause of the mismatch has not been established.

Existing ventilation control, humidity boost, CO2, and shower automations were found. Leave migration for a separate step after the integration works. Inspect their full configurations and references before changing them; avoid creating a feedback loop between the helper and the new entity.

## Proposed first release

1. **Protocol client and parser.** Add an asynchronous HTTP client using Home Assistant's shared aiohttp session. Separate parsing from transport. Validate positions strictly as 1–4, bound timeouts and response size, and distinguish connection failures, HTTP failures, and unsupported HTML. Serialize reads and writes to avoid races and excess load on the embedded server.
2. **Manual configuration and lifecycle.** Use domain `sanutal_air` in `custom_components/sanutal_air/`. Add a UI config flow accepting host and port, validate with GET, reject duplicate endpoints, support reconfiguration and unload/reload. Do not require YAML or cloud credentials. Set IoT class to `local_polling`.
3. **Observed state and control.** Expose one select entity named Ventilation position with options `1`, `2`, `3`, `4`. Its current option is read from the device, so a separate speed sensor is unnecessary. Do not invent an off command or equate the four positions to evenly spaced fan percentages.
4. **Coordinator.** Start with a 30-second polling interval, subject to device testing. After a selection POST, perform a bounded readback with a short delay if necessary. Update from observed state, not just HTTP success. Report errors clearly; mark unavailable when polling fails and recover on the next successful read. Do not automatically replay writes after ambiguous transport failures. External controls may change the position again.
5. **Discovery.** Add Zeroconf setup confirmation, device fingerprint validation, manual/discovered duplicate handling, and conservative address updates tied to verified identity. If stable identity remains unavailable, retain explicit reconfiguration rather than silently merging unrelated units.
6. **Packaging.** Add manifest, strings/translations, README installation and troubleshooting instructions, license, release version, and CI. Keep all runtime code within the integration directory. Initial Git installation means copying `custom_components/sanutal_air` to the Home Assistant config directory, restarting, and adding the integration through Settings. Later support HACS custom-repository installation and then default-list submission; those are separate milestones.

References: [select entity](https://developers.home-assistant.io/docs/core/entity/select/), [coordinator and fetching data](https://developers.home-assistant.io/docs/integration_fetching_data/), [config flows](https://developers.home-assistant.io/docs/core/integration/config_flow/), [HACS requirements](https://www.hacs.xyz/docs/publish/integration/).

## Validation and release gates

- Parser fixtures for each of the four state scripts, misleading click-handler code, whitespace/quote variations, missing or conflicting selections, and unrelated/malformed HTML. Use minimal authored fixtures rather than publishing the entire vendor UI.
- Mock HTTP tests for the exact URL/body, invalid inputs, timeout, non-success status, invalid payload, and write/readback behavior.
- Home Assistant tests for manual and discovered setup, duplicates, reconfiguration, unavailable/recovery, select commands, and unloading. Run lint and integration validation against a documented minimum Home Assistant version.
- Controlled live validation: record the initial position, select each position, read it back, check physical/app changes are reflected, and restore the initial position. Account for active automations that may override the test. This validation is outstanding and was not performed as part of research.
- Verify discovery from the actual Home Assistant network and confirm identity behavior before enabling automatic host updates.
- Install from the repository in the user's Home Assistant and validate restart/reload behavior before migrating automations or releasing.

## Android decompilation

Yes: an APK can be inspected with [JADX](https://github.com/skylot/jadx), which decompiles Android bytecode and decodes resources, although reconstruction is not always complete. An APK exported from an installed copy can reveal endpoint strings, discovery logic, assets, or a simpler state API. Hybrid apps may place useful code in bundled web assets instead of Java classes.

Follow-up: the user supplied version 26.8.18 as an XAPK, and its .NET MAUI application assembly was successfully extracted and decompiled with ILSpy. The app loads the entered device address in a WebView; no separate API or discovery implementation was found in its application code. This supports the protocol plan above, while stable device identity and live write/readback remain unresolved. See [Android inspection](android-inspection.md) for evidence and methodology. Vendor binaries and recovered source are kept out of the integration repository.

## Implementation status (2026-10-07)

Version 0.1.0 is implemented in `custom_components/sanutal_air`: serialized HTTP
client, restricted state parser, config flow, discovery confirmation, reconfiguration,
coordinator, and select entity. Entity identities are entry-based; automatic address
migration is deliberately omitted because hardware identity is unresolved.

Validation: 27 automated tests passed on Home Assistant 2026.10.0b4, Ruff lint and
format checks passed, and direct hassfest validation reported zero invalid integrations.
The Docker validator could not access the local daemon, so the upstream validator
was run directly from a temporary Home Assistant core checkout.

The live client read position 3, selected and confirmed positions 1–4, then restored
and confirmed position 3. The earlier read-only investigation notes above describe
the research phase; this later implementation test did send control commands.

Remaining deployment checks: install/restart in the actual Home Assistant instance,
confirm multicast discovery there, and validate updates originating from physical
controls. Existing automations and helpers have not been changed. GitHub publication
and HACS default-list submission have not been performed.
