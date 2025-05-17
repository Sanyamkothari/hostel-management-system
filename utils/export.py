"""
Export utilities for generating PDF and CSV files
"""
import csv
import os
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
            headers = data[0].keys()
        
        writer = csv.writer(output)
        
        # Write headers if available
        if headers:
            writer.writerow(headers)
        
        # Write data rows
        if data:
            if isinstance(data[0], dict):
                for row in data:
                    writer.writerow([row.get(key, '') for key in headers])
            else:
                writer.writerows(data)
        
        # Create response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-type'] = 'text/csv'
        
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
        
        # Prepare table data
        table_data = []
        if headers:
            table_data.append(headers)
        
        # Add data rows
        if data:
            if isinstance(data[0], dict):
                for row in data:
                    table_data.append([row.get(key, '') for key in headers])
            else:
                table_data.extend(data)
        
        # Create table
        if table_data:
            table = Table(table_data)
            
            # Style the table
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
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
            mimetype='application/pdf'
        )
