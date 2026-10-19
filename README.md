# pogo-calendar

Filtered Pokémon GO event calendars you can subscribe to. They rebuild daily on GitHub Actions and are served from GitHub Pages.

- Choose what to drop, or move to the long calendar, in `config.toml` using regexes on event titles.
- Preview with `python build.py --list` (needs `pip install icalendar`). Each event is marked short, LONG or drop.
- Subscribe in Google Calendar (Other calendars → + → From URL) to one or both:
  - `https://<user>.github.io/pogo-calendar/pokemon-go.ics`: events up to a day long
  - `https://<user>.github.io/pogo-calendar/pokemon-go-long.ics`: multi-day events (Halloween, Minior Showers, weekend Shadow Raids, etc.)
- Events longer than `long_event_hours` in `config.toml` go into the long calendar.

The source is the "GO Local Events (UTC-7)" calendar. Despite its name, its event times follow Pacific time including daylight saving, so they're passed through unchanged. `timezone` in `config.toml` only sets the display zone and the calendar names.

Event data comes from the volunteer-run "GO Local Events" Google Calendar (pogoeventcalendar@gmail.com).
