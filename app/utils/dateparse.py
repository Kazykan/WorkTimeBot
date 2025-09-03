from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytz


def parse_russian_date(date_str: str, timezone_name: str = "Europe/Moscow") -> Optional[datetime]:
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


def parse_time(time_str: str, date: datetime, timezone_name: str = "Europe/Moscow") -> Optional[datetime]:
    """
    Parse time string in format HH:MM or HH.MM
    Returns datetime with specified date and time
    """
    try:
        # Handle different time formats
        if ":" in time_str:
            hour, minute = map(int, time_str.split(":"))
        elif "." in time_str:
            hour, minute = map(int, time_str.split("."))
        else:
            # Assume HHMM format
            if len(time_str) == 4:
                hour, minute = int(time_str[:2]), int(time_str[2:])
            else:
                return None
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        
        tz = pytz.timezone(timezone_name)
        return tz.localize(datetime.combine(date.date(), datetime.min.time().replace(hour=hour, minute=minute)))
        
    except (ValueError, IndexError):
        return None


def calculate_hours(start_time: datetime, end_time: datetime) -> float:
    """
    Calculate hours between start and end time
    """
    if start_time >= end_time:
        return 0.0
    
    delta = end_time - start_time
    return round(delta.total_seconds() / 3600, 2)  # Round to 2 decimal places
