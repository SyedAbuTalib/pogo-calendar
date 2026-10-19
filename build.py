"""Build filtered Pokémon GO .ics calendars from the "GO Local Events" Google Calendar."""

import argparse
import re
import sys
import tomllib
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import icalendar

ROOT = Path(__file__).parent


def fetch_calendar(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return icalendar.Calendar.from_ical(resp.read())


def duration_hours(event):
    start = event["DTSTART"].dt
    if "DTEND" in event:
        end = event["DTEND"].dt
    elif "DURATION" in event:
        end = start + event["DURATION"].dt
    else:
        # No end: an all-day date lasts one day, a timed event is a marker.
        end = start + timedelta(days=1) if not isinstance(start, datetime) else start
    if isinstance(start, datetime):
        return (end - start).total_seconds() / 3600
    return (end - start).days * 24


def end_time(event):
    start = event["DTSTART"].dt
    if "RRULE" in event:
        until = event["RRULE"].get("UNTIL")
        return until[0] if until else None
    end = event["DTEND"].dt if "DTEND" in event else start
    return end if isinstance(end, datetime) else datetime(end.year, end.month, end.day, tzinfo=timezone.utc)


def matches(event, patterns):
    return any(re.search(p, str(event["SUMMARY"]), re.IGNORECASE) for p in patterns)


def build_ics(events, name, tz):
    cal = icalendar.Calendar()
    cal.add("PRODID", "-//pogo-calendar//EN")
    cal.add("VERSION", "2.0")
    cal.add("CALSCALE", "GREGORIAN")
    cal.add("METHOD", "PUBLISH")
    cal.add("X-WR-CALNAME", name)
    cal.add("X-WR-TIMEZONE", tz.key)
    cal.add("X-WR-CALDESC", "Filtered from the GO Local Events calendar (pogoeventcalendar@gmail.com)")
    cal.add("REFRESH-INTERVAL", timedelta(days=1), parameters={"VALUE": "DURATION"})
    cal.add("X-PUBLISHED-TTL", timedelta(days=1))
    for e in events:
        cal.add_component(e)
    cal.add_missing_timezones()
    return cal.to_ical()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=ROOT / "config.toml", type=Path)
    parser.add_argument("--out-dir", default=ROOT / "public", type=Path)
    parser.add_argument("--list", action="store_true", help="show upcoming events and where they go")
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text())
    name = config.get("calendar_name", "Pokémon GO")
    tz = ZoneInfo(config.get("timezone", "America/Los_Angeles"))
    limit = config.get("long_event_hours", 24)
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.get("keep_past_days", 30))

    source = fetch_calendar(config["source_url"])
    short, long, dropped = [], [], []
    for e in source.walk("VEVENT"):
        end = end_time(e)
        if end is not None and end < cutoff:
            continue
        # Markers like "GO Battle Thursday" have no end; Google would show
        # them as 1 hour, so make them zero-length like the source calendar.
        if "DTEND" not in e and "DURATION" not in e and isinstance(e["DTSTART"].dt, datetime):
            e.add("DTEND", e["DTSTART"].dt)
        if matches(e, config.get("exclude_name_patterns", [])):
            dropped.append(e)
        elif matches(e, config.get("long_name_patterns", [])) or duration_hours(e) > limit:
            long.append(e)
        else:
            short.append(e)

    if args.list:
        rows = [("short", e) for e in short] + [("LONG ", e) for e in long] + [("drop ", e) for e in dropped]
        for mark, e in sorted(rows, key=lambda r: str(r[1]["DTSTART"].dt)):
            print(f"{mark}  {str(e['DTSTART'].dt)[:16]}  {e['SUMMARY']}")
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for filename, cal_name, cal_events in [
        ("pokemon-go.ics", f"{name} ({tz.key})", short),
        ("pokemon-go-long.ics", f"{name} long events ({tz.key})", long),
    ]:
        out = args.out_dir / filename
        out.write_bytes(build_ics(cal_events, cal_name, tz))
        print(f"wrote {len(cal_events)} events to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
