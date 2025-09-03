from __future__ import annotations

from datetime import datetime
from typing import Any

from app.utils.dateparse import format_russian_date


def format_currency(amount_kopecks: int) -> str:
    """
    Format amount in kopecks to rubles string
    """
    rubles = amount_kopecks // 100
    kopecks = amount_kopecks % 100
    
    if kopecks == 0:
        return f"{rubles:,} р.".replace(",", " ")
    else:
        return f"{rubles:,}.{kopecks:02d} р.".replace(",", " ")


def format_hours(hours: float) -> str:
    """
    Format hours with proper Russian word forms
    """
    if hours == 1.0:
        return "1 час"
    elif 2.0 <= hours <= 4.0:
        return f"{hours} часа"
    else:
        return f"{hours} часов"


def format_work_days(days: int) -> str:
    """
    Format work days with proper Russian word forms
    """
    if days == 1:
        return "1 день"
    elif 2 <= days <= 4:
        return f"{days} дня"
    else:
        return f"{days} дней"


def format_rate(amount_kopecks: int, hours: int) -> str:
    """
    Calculate and format hourly rate
    """
    if hours == 0:
        return "0 р./час"
    
    # Convert kopecks to rubles first, then divide
    amount_rubles = amount_kopecks / 100
    rate_rubles = amount_rubles / hours
    
    # Round to nearest ruble
    rate_rubles_rounded = round(rate_rubles)
    
    return f"{rate_rubles_rounded:,} р./час".replace(",", " ")


def format_date_range(start_date: datetime, end_date: datetime) -> str:
    """
    Format date range for reports
    """
    start_str = format_russian_date(start_date)
    end_str = format_russian_date(end_date)
    
    if start_str == end_str:
        return start_str
    else:
        return f"{start_str} - {end_str}"


def format_month_year(dt: datetime) -> str:
    """
    Format month and year in Russian
    """
    months = {
        1: "январе", 2: "феврале", 3: "марте", 4: "апреле",
        5: "мае", 6: "июне", 7: "июле", 8: "августе",
        9: "сентябре", 10: "октябре", 11: "ноябре", 12: "декабре"
    }
    
    month_name = months[dt.month]
    year = dt.year
    
    return f"{month_name} {year}"
