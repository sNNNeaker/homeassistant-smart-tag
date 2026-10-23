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

1. In HACS, open the menu, choose "Custom repositories" and add `https://github.com/sNNNeaker/homeassistant-smart-tag` as category "Integration".
1. Install "SMART tag" and restart Home Assistant.
1. Go to Settings -> Devices & services -> Add integration -> "SMART tag" and log in with your parent portal email and password. The password is not stored, only the session tokens.

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
