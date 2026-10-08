# HACS default-list submission

Reviewed against the [HACS submission requirements](https://www.hacs.xyz/docs/publish/include/)
on 2026-10-08.

## Repository readiness

- Public GitHub repository owned by the submitting account.
- Description, topics, issues, README, and license present.
- One integration in `custom_components/sanutal_air/` with versioned manifest.
- Root `hacs.json` with name and minimum Home Assistant version.
- HACS custom-repository installation supported.
- HACS validation workflow without ignored checks, plus hassfest and tests.
- Bundled `brand/icon.png`; inclusion in the upstream brands repository is unnecessary.
- Full GitHub release must be published after validation workflows succeed.

No country restriction is applied: local device support is usable wherever compatible
hardware is installed. The integration is independent of Home Assistant Core and does
not override a built-in integration.

## Submission procedure

1. Verify the latest HACS and Tests workflow runs succeeded; Tests includes hassfest.
2. Publish a full GitHub release matching the integration manifest version, targeting
   that validated commit. A tag alone is insufficient. HACS can download the source
   archive; this layout requires no separate ZIP asset or `zip_release` setting.
3. Fork `hacs/default`, create a new branch from its `master`, and insert
   `eliaslecomte/homeassistant-sanutal-air` into the `integration` JSON list in
   alphabetical order.
4. Open a pull request with maintainer edits enabled. Complete its current template
   and include links to the full release, successful HACS run, and successful Tests
   run showing hassfest. Do not request reviews; allow the normal queue to process it.

Default-list submission and acceptance are distinct from custom-repository support.
Track the PR checks and address reviewer feedback when submission is made.

## Compatibility follow-up

The declared compatibility floor is Home Assistant 2026.3.0. Installed behavior is
confirmed on 2026.10.0; the pinned automated harness uses 2026.10.0b4. Testing the
minimum version is a remaining compatibility task, not a completed verification.
