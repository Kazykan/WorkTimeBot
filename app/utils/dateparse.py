from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Optional

import pytz # type: ignore


def parse_russian_date(
    date_str: str, timezone_name: str = "Europe/Moscow"
) -> Optional[datetime]:
    """
    Parse date string in format DD.MM.YY or DD.MM.YYYY
    Returns datetime in specified timezone
    """
    try:
        # Try DD.MM.YY format first
        if len(date_str.split(".")[-1]) == 2:
            dt = datetime.strptime(date_str, "%d.%m.%y")
            # Assume 20xx for 2-digit years
            dt = dt.replace(year=dt.year + 2000)
        else:
            # DD.MM.YYYY format
            dt = datetime.strptime(date_str, "%d.%m.%Y")

        # Set time to midnight in the specified timezone
        tz = pytz.timezone(timezone_name)
        dt = tz.localize(dt)

        return dt
    except (ValueError, IndexError):
        return None


def format_russian_date(dt: datetime, timezone_name: str = "Europe/Moscow") -> str:
    """
    Format datetime to DD.MM.YY string in specified timezone
    """
    tz = pytz.timezone(timezone_name)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%d.%m.%y")


def get_today_in_timezone(timezone_name: str = "Europe/Moscow") -> datetime:
    """
    Get today's date at midnight in specified timezone
    """
    tz = pytz.timezone(timezone_name)
    now = datetime.now(tz)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_time(
    time_str: str, date: datetime, timezone_name: str = "Europe/Moscow"
) -> Optional[datetime]:
    """
    Parse time string in formats:
    HH:MM, HH.MM, HH MM, HHMM, H, HH, H M, HH M, etc.
    Returns datetime with specified date and time
    """
    try:
        time_str = time_str.strip()
        # Заменяем все разделители на пробел
        for sep in [":", ".", "-"]:
            time_str = time_str.replace(sep, " ")

        parts = time_str.split()

        if len(parts) == 2:
            hour, minute = map(int, parts)
        elif len(parts) == 1:
            val = parts[0]
            if len(val) == 4 and val.isdigit():
                hour, minute = int(val[:2]), int(val[2:])
            elif len(val) <= 2 and val.isdigit():
                hour, minute = int(val), 0
            else:
                return None
        else:
            return None

        # Проверка диапазонов
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        tz = pytz.timezone(timezone_name)
        return tz.localize(
            datetime.combine(
                date.date(), datetime.min.time().replace(hour=hour, minute=minute)
            )
        )

    except (ValueError, IndexError):
        return None


def parse_date(user_input: str | None) -> Optional[datetime]:
    """
    Принимает дату в формате ДД.ММ.ГГ или ДД.ММ.ГГГГ
    Возвращает datetime или None, если формат неверный
    """
    if not user_input:
        return None
    user_input = user_input.strip()
    for fmt in ("%d.%m.%y", "%d.%m.%Y"):
        try:
            date = datetime.strptime(user_input, fmt)
            # Дополнительная защита от странных годов
            if date.year < 2000 or date.year > 2100:
                return None
            return date
        except ValueError:
            continue
    return None


def calculate_hours(start_time: datetime, end_time: datetime) -> float:
    """
    Calculate hours between start and end time
    """
    if start_time >= end_time:
        return 0.0

    delta = end_time - start_time
    return round(delta.total_seconds() / 3600, 2)  # Round to 2 decimal places


def hours_to_str(hours: float) -> str:
    """
    Преобразует часы в формате float (например, 7.75)
    в строку формата HH:MM (например, '7:45')
    """
    h = int(hours)
    m = int(round((hours - h) * 60))
    if m == 60:  # защита от округления 59.999 → 60
        h += 1
        m = 0
    return f"{h}:{m:02d}"
