# filepath: c:\Users\sanya\OneDrive\Desktop\hostel_management_v2\utils\export.py
"""
Export utilities for generating PDF and CSV files
"""
import csv
import os
import tempfile
from datetime import datetime
import io
from flask import make_response, send_file

# Check if reportlab is available for PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class ExportUtility:
    """Utility class for exporting data to different formats"""
    
    @staticmethod
    def export_data(data, filename, format_type='csv', title="Report", description=None, headers=None):
        """
        Export data to specified format (CSV or Excel)
        
        Args:
            data: List of dictionaries with data to export
            filename: Name of the file to create (without extension)
            format_type: Export format ('csv' or 'excel')
            title: Title for the document
            description: Optional description
            headers: List of headers for the columns
            
        Returns:
            Response object with file
        """
        if format_type.lower() in ['excel', 'xlsx']:
            # For Excel format, use CSV for now as a fallback
            return ExportUtility.export_to_csv(data, f"{filename}.csv", headers)
        else:
            # Default to CSV
            return ExportUtility.export_to_csv(data, f"{filename}.csv", headers)
    
    @staticmethod
    def export_to_csv(data, filename, headers=None):
        """
        Export data to CSV file
        
        Args:
            data: List of dictionaries or list of lists with data to export
            filename: Name of the CSV file to create
            headers: List of headers for the CSV columns
            
        Returns:
            Response object with CSV file
        """
        output = io.StringIO()
        
        # Determine headers if not provided
        if not headers and data and isinstance(data[0], dict):
            headers = list(data[0].keys())
        
        # Ensure headers is not None to avoid iteration errors
        headers = headers or []
        
        writer = csv.writer(output)
        
        # Write headers if available
        if headers:
            writer.writerow(headers)
        
        # Write data rows
        if data:
            if isinstance(data[0], dict):
                for row in data:
                    writer.writerow([row.get(key, "") for key in headers])
            else:
                writer.writerows(data)
        
        # Create response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-type"] = "text/csv"
        
        return response
    
    @staticmethod
    def export_to_pdf(data, filename, title="Report", description=None, headers=None):
        """
        Export data to PDF file
        
        Args:
            data: List of dictionaries or list of lists with data to export
            filename: Name of the PDF file to create
            title: Title for the PDF document
            description: Optional description text
            headers: List of headers for the table columns
            
        Returns:
            Response object with PDF file or None if reportlab is not available
        """
        if not REPORTLAB_AVAILABLE:
            return None
            
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Set up styles
        styles = getSampleStyleSheet()
        title_style = styles["Heading1"]
        subtitle_style = styles["Heading2"]
        normal_style = styles["Normal"]
        
        # Add title
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated on: {timestamp}", normal_style))
        elements.append(Spacer(1, 12))
        
        # Add description if provided
        if description:
            elements.append(Paragraph(description, normal_style))
            elements.append(Spacer(1, 12))
        
        # Determine headers if not provided
        if not headers and data and isinstance(data[0], dict):
            headers = list(data[0].keys())
        
        # Ensure headers is not None to avoid iteration errors
        headers = headers or []
        
        # Prepare table data
        table_data = []
        if headers:
            table_data.append(headers)
        
        # Add data rows
        if data:
            if isinstance(data[0], dict):
                for row in data:
                    table_data.append([row.get(key, "") for key in headers])
            else:
                table_data.extend(data)
        
        # Create table
        if table_data:
            table = Table(table_data)
            
            # Style the table
            style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ])
            table.setStyle(style)
            elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # Create response
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )
    
    @staticmethod
    def export_rooms_to_csv(rooms_data):
        """Export room data to CSV format and return a file path"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"rooms_export_{timestamp}.csv"
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", newline="")
        
        # Define CSV headers
        headers = ["Room Number", "Capacity", "Current Occupancy", "Status", "Occupancy Percentage"]
        
        writer = csv.writer(temp_file)
        writer.writerow(headers)
        
        # Write data rows
        for room in rooms_data or []:  # Use empty list if rooms_data is None
            if isinstance(room, dict):
                # Map headers to keys in the room dict (handle possible mismatch)
                row_data = [
                    room.get("Room Number", room.get("room_number", "")),
                    room.get("Capacity", room.get("capacity", "")),
                    room.get("Current Occupancy", room.get("current_occupancy", "")),
                    room.get("Status", room.get("status", "")),
                    room.get("Occupancy Percentage", room.get("occupancy_percentage", "")),
                ]
                writer.writerow(row_data)
            else:
                writer.writerow(room)
        
        temp_file.close()
        return temp_file.name
    
    @staticmethod
    def export_rooms_to_pdf(rooms_data):
        """Export room data to PDF format and return a file path"""
        if not REPORTLAB_AVAILABLE:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"rooms_export_{timestamp}.pdf"
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.close()
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(temp_file.name, pagesize=A4)
            elements = []
            
            # Set up styles
            styles = getSampleStyleSheet()
            title_style = styles["Heading1"]
            normal_style = styles["Normal"]
            
            # Add title
            elements.append(Paragraph("Rooms Occupancy Report", title_style))
            elements.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elements.append(Paragraph(f"Generated on: {timestamp_str}", normal_style))
            elements.append(Spacer(1, 12))
            
            # Define headers
            headers = ["Room Number", "Capacity", "Current Occupancy", "Status", "Occupancy Percentage"]
            
            # Prepare table data
            table_data = [headers]
            
            # Add data rows
            for room in rooms_data or []:  # Use empty list if rooms_data is None
                if isinstance(room, dict):
                    row_data = []
                    for key in headers:
                        row_data.append(room.get(key, ""))
                    table_data.append(row_data)
                else:
                    table_data.append(room)
            
            # Create table
            if table_data:
                table = Table(table_data)
                
                # Style the table
                style = TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ])
                table.setStyle(style)
                elements.append(table)
            
            # Build PDF
            doc.build(elements)
            
            return temp_file.name
        except Exception as e:
            # If any error occurs during PDF generation, return None
            print(f"Error generating PDF: {str(e)}")
            return None
