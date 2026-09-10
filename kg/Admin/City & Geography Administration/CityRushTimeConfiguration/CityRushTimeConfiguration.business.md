---
id: 8orders/admin/city-and-geography-administration/cityrushtimeconfiguration-business
note_type: business
context: Admin
feature: City & Geography Administration
entity: CityRushTimeConfiguration
entity_type: legacy-poco-root
last_updated: 2026-08-23
tags: [admin, delivery, transactional, business]
---
# CityRushTimeConfiguration

A city's "we're too busy right now" mode — automatically triggered when too many delivery requests
are timing out, and lifted once things calm down.

## What it is
Each city has a rush-mode configuration: a threshold for how many timed-out delivery requests count
as "busy", and a lower threshold for when it's safe to reopen. While in rush mode, individual areas
within the city can independently be marked busy or not, based on their own request load, using a
priority ordering set up in advance.

## Business rules (plain words)
- Rush mode turns on automatically once timed-out requests reach the busy threshold, and can turn off
  automatically once they drop below the reopen threshold (a lower number than the busy threshold, by
  design).
- Every rush-mode period is logged, with a start and end time and how many orders happened during it.
- While rush mode is active, the core thresholds (busy/reopen/check-interval) are frozen — you can't
  change them until rush mode ends, though the configuration can still be deactivated outright at any
  time.
- Adding or deleting an area's priority ranking is blocked while rush mode is active; updating an
  existing one's settings is not (see the technical note's Open Question about whether that's
  deliberate).
- The same geographic area can't be assigned to two different priority rankings at once.
- There's also an admin "force end" override — but see the technical note for a likely bug in its
  guard logic.

## Who uses it
- **Roles:** Admin (configures thresholds and area priorities); the system itself evaluates and
  flips rush mode automatically based on live request data.

## Related
- [[City.technical|City]] — the city this configuration belongs to
- Technical detail: [[CityRushTimeConfiguration.technical|CityRushTimeConfiguration — technical]]
