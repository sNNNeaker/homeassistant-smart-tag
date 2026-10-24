<p align="center">
  <!-- Plain <img> with an absolute URL: the HACS/Marketplace README renderer
       doesn't support <picture>/<source>, and relative paths only resolve on
       GitHub. -->
  <img alt="SMART tag" src="https://raw.githubusercontent.com/sNNNeaker/homeassistant-smart-tag/main/custom_components/smart_tag/brand/logo%402x.png" width="420">
</p>

# SMART tag Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]

_Integration for the [SMART tag parent portal](https://parent.smart-tag.net) (school bus tracking)._

**Unofficial:** this project is not affiliated with or endorsed by SMART tag. It is a fork of [grimsteel/homeassistant-smart-tag](https://github.com/grimsteel/homeassistant-smart-tag); credit for the original API client and idea goes to grimsteel.

## Entities

One config entry per parent account. For every student linked to the account a device is created with:

Entity | Description
-- | --
On bus (`binary_sensor`) | Whether the student is currently on a bus.
Bus status (`sensor`) | `on_bus`, `dropped_off` or `no_ride_today`. Attributes describe the latest ride: `bus`, `route`, `driver`, `shift`, `boarded_at`, `boarded_latitude`, `boarded_longitude`, `dropped_off_at`, `dropped_off_latitude`, `dropped_off_longitude`.

## Options

Polling is adaptive: every minute inside a ride window or while a student is on the bus, otherwise at most every 30 minutes (and in time for the next window). Configure under the integration's options:

- Morning start / end (default 06:30 - 08:45)
- Afternoon start / end (default 14:30 - 17:00)
- Weekdays only (default on)

## Installation

SMART tag is in the HACS community catalog, so you can find it by name; no custom repository is needed.

### Via the Marketplace (Home Assistant 2026.11 and newer)

From 2026.11 HACS is built into Home Assistant as the **Marketplace** (Settings → Marketplace).

1. Search for **SMART tag** and download it. Catalog entries install from the release asset, so no GitHub connection is needed, and no restart is needed on first install.
2. Settings → Devices & services → Add integration → **SMART tag**, or use
   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smart_tag)

Updates show up under Settings → Updates; installing an update needs a restart, which the Marketplace offers via a repair.

### Via HACS (Home Assistant 2026.10 and older)

1. In HACS, search for **SMART tag** and download it.
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → **SMART tag**.

If you added this repository as a custom repository before it joined the catalog, that keeps working; you can remove the custom entry (HACS ⋮ menu → Custom repositories) without uninstalling.

### Manual

Copy `custom_components/smart_tag/` to `config/custom_components/smart_tag/`, restart Home Assistant, then add the integration as above.

### Setup

Log in with your parent portal email and password. The password is not stored, only the session tokens.

## Roadmap

Planned or under consideration, no promises:

- Live bus location as a `device_tracker` while a student is on the bus, plus a "bus approaching" binary sensor (needs the portal's authenticated live-location endpoint, not identified yet).
- Timestamp sensors for boarding and drop-off times.
- Event entities (`boarded`, `dropped_off`) for automations.
- Ride windows from a school calendar or learned from ride history; skip holidays.
- Diagnostics download, tests.

## License

GPL-3.0, see [LICENSE](LICENSE).

[commits-shield]: https://img.shields.io/github/commit-activity/y/sNNNeaker/homeassistant-smart-tag.svg?style=for-the-badge
[commits]: https://github.com/sNNNeaker/homeassistant-smart-tag/commits/main

[releases-shield]: https://img.shields.io/github/release/sNNNeaker/homeassistant-smart-tag.svg?style=for-the-badge
[releases]: https://github.com/sNNNeaker/homeassistant-smart-tag/releases
