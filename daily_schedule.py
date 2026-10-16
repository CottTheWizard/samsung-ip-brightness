"""Daily local-time schedule, independent of GUI and network."""
from datetime import datetime, timedelta


def parse_schedule(text: str) -> list[dict]:
    entries = []
    seen = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            clock, raw = line.strip().split('=')
            hour, minute = clock.strip().split(':')
            if len(hour) != 2 or len(minute) != 2:
                raise ValueError()
            hour, minute, value = int(hour), int(minute), int(raw)
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= value <= 50):
                raise ValueError()
            key = f'{hour:02}:{minute:02}'
            if key in seen:
                raise ValueError()
            seen.add(key)
            entries.append({'time': key, 'brightness': value})
        except (ValueError, TypeError):
            raise ValueError('Use HH:MM=brightness (0–50), one unique time per line.') from None
    if not entries:
        raise ValueError('Add at least one daily time.')
    return sorted(entries, key=lambda entry: entry['time'])


def current_slot(entries: list[dict], now: datetime) -> tuple[str, int]:
    """Last local wall-clock entry, including the previous day's last entry."""
    if not entries:
        raise ValueError('Empty schedule')
    candidates = []
    for entry in entries:
        hour, minute = map(int, entry['time'].split(':'))
        when = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if when > now:
            when -= timedelta(days=1)
        candidates.append((when, entry['brightness']))
    when, value = max(candidates, key=lambda item: item[0])
    return when.isoformat(), value


class ScheduleState:
    """One successful write per slot; retry failed writes after 60 seconds."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.applied = None
        self.pending = None
        self.last_attempt = float('-inf')

    def due(self, entries, now, monotonic):
        key, value = current_slot(entries, now)
        if key == self.applied or self.pending is not None or monotonic - self.last_attempt < 60:
            return None
        self.pending = key
        self.last_attempt = monotonic
        return key, value

    def finish(self, key, success):
        if self.pending == key:
            self.pending = None
            if success:
                self.applied = key
