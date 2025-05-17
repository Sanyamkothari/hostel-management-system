"""
General utility functions for the Hostel Management System
"""
import json
import csv
import io
from flask import Response
from datetime import date, datetime

def to_dict(row):
    """Convert a sqlite3.Row to a dictionary."""
    return {key: row[key] for key in row.keys()}

def format_currency(amount):
    """Format a currency amount."""
    if amount is None:
        return "$0.00"
    
    return f"${amount:,.2f}"

def export_to_csv(data, filename, headers=None):
    """Export data to a CSV file."""
    if not data:
        return None
    
    # Create a StringIO object for CSV data
    si = io.StringIO()
    
    # Determine headers if not provided
    if not headers and data:
        if isinstance(data[0], dict):
            headers = data[0].keys()
    
    writer = csv.DictWriter(si, fieldnames=headers)
    writer.writeheader()
    
    # Write the data
    for row in data:
        # Convert sqlite3.Row to dict if needed
        if not isinstance(row, dict):
            row = to_dict(row)
        
        # Handle date objects
        for key, value in row.items():
            if isinstance(value, (date, datetime)):
                row[key] = value.isoformat()
        
        writer.writerow(row)
    
    # Create a Flask response with CSV data
    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return output

def export_to_json(data, filename):
    """Export data to a JSON file."""
    if not data:
        return None
    
    # Convert data to list of dicts if not already
    data_dicts = []
    for row in data:
        if not isinstance(row, dict):
            row = to_dict(row)
        
        # Handle date objects
        for key, value in row.items():
            if isinstance(value, (date, datetime)):
                row[key] = value.isoformat()
        
        data_dicts.append(row)
    
    # Create a Flask response with JSON data
    output = Response(
        json.dumps(data_dicts, indent=2),
        mimetype='application/json'
    )
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return output

class Pagination:
    """Simple pagination class."""
    def __init__(self, items, page=1, per_page=10):
        self.items = items
        self.page = page
        self.per_page = per_page
        
    @property
    def total(self):
        """Total number of items."""
        return len(self.items)
    
    @property
    def pages(self):
        """Total number of pages."""
        return max(1, (self.total + self.per_page - 1) // self.per_page)
    
    @property
    def has_prev(self):
        """Whether there is a previous page."""
        return self.page > 1
    
    @property
    def has_next(self):
        """Whether there is a next page."""
        return self.page < self.pages
    
    @property
    def current_items(self):
        """Items on the current page."""
        start = (self.page - 1) * self.per_page
        end = min(start + self.per_page, self.total)
        return self.items[start:end]
    
    def iter_pages(self, left_edge=2, left_current=2,
                  right_current=3, right_edge=2):
        """Iterate over page numbers to display."""
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num
