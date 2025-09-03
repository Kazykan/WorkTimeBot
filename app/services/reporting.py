from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple

from app.models.payment import Payment
from app.models.time_entry import TimeEntry
from app.models.work_object import WorkObject
from app.utils.formatting import (
    format_currency,
    format_date_range,
    format_hours,
    format_month_year,
    format_rate,
    format_work_days,
)


class ReportingService:
    @staticmethod
    def generate_object_report(
        work_object: WorkObject,
        time_entries: List[TimeEntry],
        payments: List[Payment]
    ) -> str:
        """Generate report for a single work object"""
        total_hours = sum(entry.hours for entry in time_entries)
        total_payments = sum(payment.amount for payment in payments)
        
        if total_hours == 0:
            return f"{work_object.name} — 0ч — {format_currency(total_payments)}"
        
        # Calculate work days (unique dates with time entries)
        work_dates = set(entry.date.date() for entry in time_entries)
        work_days = len(work_dates)
        
        # Calculate hourly rate
        rate_str = format_rate(total_payments, total_hours)
        
        return (
            f"{work_object.name} — {format_hours(total_hours)} "
            f"({format_work_days(work_days)} д. работы) — "
            f"{format_currency(total_payments)} ({rate_str})"
        )

    @staticmethod
    def generate_period_report(
        objects: List[WorkObject],
        time_entries: List[TimeEntry],
        payments: List[Payment],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Generate report for a specific period"""
        if not objects:
            return "📊 За указанный период нет данных."
        
        # Group entries by object
        object_entries = {}
        object_payments = {}
        
        for entry in time_entries:
            if entry.work_object_id not in object_entries:
                object_entries[entry.work_object_id] = []
            object_entries[entry.work_object_id].append(entry)
        
        for payment in payments:
            if payment.work_object_id not in object_payments:
                object_payments[payment.work_object_id] = []
            object_payments[payment.work_object_id].append(payment)
        
        # Generate object reports
        object_reports = []
        total_hours = 0
        total_payments = 0
        
        for obj in objects:
            entries = object_entries.get(obj.id, [])
            obj_payments = object_payments.get(obj.id, [])
            
            object_report = ReportingService.generate_object_report(obj, entries, obj_payments)
            object_reports.append(object_report)
            
            total_hours += sum(entry.hours for entry in entries)
            total_payments += sum(payment.amount for payment in obj_payments)
        
        # Calculate overall statistics
        all_work_dates = set()
        for entries in object_entries.values():
            all_work_dates.update(entry.date.date() for entry in entries)
        
        work_days = len(all_work_dates)
        total_days = (end_date.date() - start_date.date()).days + 1
        
        # Calculate average hourly rate
        avg_rate_str = format_rate(total_payments, total_hours) if total_hours > 0 else "0 р./час"
        
        # Build report
        report_lines = object_reports
        report_lines.append("")  # Empty line
        report_lines.append(f"Итого: {format_currency(total_payments)} ({avg_rate_str})")
        report_lines.append(f"{format_work_days(work_days)} рабочих дней из {total_days} дней в {format_month_year(start_date)}")
        
        return "\n".join(report_lines)

    @staticmethod
    def get_last_month_period() -> Tuple[datetime, datetime]:
        """Get start and end dates for last month"""
        today = datetime.now()
        
        # Get first day of current month
        first_day_current = today.replace(day=1)
        
        # Get last day of previous month
        last_day_previous = first_day_current - timedelta(days=1)
        
        # Get first day of previous month
        first_day_previous = last_day_previous.replace(day=1)
        
        return first_day_previous, last_day_previous

    @staticmethod
    def get_month_period(year: int, month: int) -> Tuple[datetime, datetime]:
        """Get start and end dates for specific month"""
        first_day = datetime(year, month, 1)
        
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        return first_day, last_day
