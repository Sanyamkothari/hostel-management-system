"""
Date utility functions for the Hostel Management System
"""
from datetime import datetime, date, timedelta
import calendar

def parse_date(date_str, formats=None):
    """
    Parse a date string into a date object.
    Tries multiple formats if provided.
    """
    if not date_str:
        return None
    
    if not formats:
        formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None

def format_date(date_obj, format_str='%Y-%m-%d'):
    """Format a date object into a string."""
    if not date_obj:
        return ''
    
    if isinstance(date_obj, str):
        date_obj = parse_date(date_obj)
        if not date_obj:
            return ''
    
    return date_obj.strftime(format_str)

def get_month_range(date_obj):
    """Get the first and last date of the month containing the given date."""
    if isinstance(date_obj, str):
        date_obj = parse_date(date_obj)
    
    first_day = date_obj.replace(day=1)
    _, last_day_num = calendar.monthrange(date_obj.year, date_obj.month)
    last_day = date_obj.replace(day=last_day_num)
    
    return first_day, last_day

def get_date_intervals(start_date, end_date, interval='month'):
    """
    Generate a list of date intervals between start_date and end_date.
    Interval can be 'day', 'week', 'month', or 'year'.
    """
    intervals = []
    
    if interval == 'day':
        current = start_date
        while current <= end_date:
            intervals.append((current, current))
            current += timedelta(days=1)
    
    elif interval == 'week':
        current = start_date
        while current <= end_date:
            week_end = min(current + timedelta(days=6), end_date)
            intervals.append((current, week_end))
            current += timedelta(days=7)
    
    elif interval == 'month':
        current_year = start_date.year
        current_month = start_date.month
        
        while (current_year < end_date.year or 
               (current_year == end_date.year and current_month <= end_date.month)):
            
            current_date = date(current_year, current_month, 1)
            _, last_day = calendar.monthrange(current_year, current_month)
            month_end = date(current_year, current_month, last_day)
            
            interval_start = max(current_date, start_date) if (current_year == start_date.year and 
                                                          current_month == start_date.month) else current_date
            interval_end = min(month_end, end_date) if (current_year == end_date.year and 
                                                      current_month == end_date.month) else month_end
            
            intervals.append((interval_start, interval_end))
            
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
    
    elif interval == 'year':
        current_year = start_date.year
        
        while current_year <= end_date.year:
            year_start = max(date(current_year, 1, 1), start_date) if current_year == start_date.year else date(current_year, 1, 1)
            year_end = min(date(current_year, 12, 31), end_date) if current_year == end_date.year else date(current_year, 12, 31)
            
            intervals.append((year_start, year_end))
            current_year += 1
    
    return intervals

def get_date_range_description(start_date, end_date):
    """Get a human-readable description of a date range."""
    if start_date == end_date:
        return format_date(start_date, '%d %b %Y')
    
    if start_date.year == end_date.year:
        if start_date.month == end_date.month:
            return f"{start_date.day} - {end_date.day} {format_date(start_date, '%b %Y')}"
        else:
            return f"{format_date(start_date, '%d %b')} - {format_date(end_date, '%d %b %Y')}"
    else:
        return f"{format_date(start_date, '%d %b %Y')} - {format_date(end_date, '%d %b %Y')}"

def format_currency(amount):
    """Format a number as currency with dollar sign and two decimal places."""
    if amount is None:
        return "$0.00"
    
    try:
        return "${:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return "$0.00"
