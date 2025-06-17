"""
Email notification utilities for the Hostel Management System
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email configuration from environment variables
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
DEFAULT_SENDER = os.environ.get("DEFAULT_SENDER", "hostel@example.com")

class EmailNotifier:
    """Handles email notifications for the hostel management system"""
    
    @staticmethod
    def send_email(to_email, subject, message_html, message_text=None, from_email=None):
        """
        Send an email using the configured SMTP server
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            message_html: HTML content of the email
            message_text: Plain text version (optional)
            from_email: Sender email (defaults to DEFAULT_SENDER)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email configuration is available
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            print("Email configuration is missing. Set SMTP_USERNAME and SMTP_PASSWORD in .env file.")
            return False
            
        from_email = from_email or DEFAULT_SENDER
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        # Attach plain text and HTML versions
        if message_text:
            msg.attach(MIMEText(message_text, 'plain'))
        
        msg.attach(MIMEText(message_html, 'html'))
        
        try:
            # Connect to SMTP server
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
              # Send email
            server.sendmail(from_email, to_email, msg.as_string())
            server.quit()
            
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
    
    @staticmethod
    def send_fee_reminder(student_id, student_name, student_email, fee_amount, due_date, days_overdue=0, hostel_name=None):
        """
        Send fee payment reminder email to a student
        
        Args:
            student_id: ID of the student
            student_name: Name of the student
            student_email: Email address of the student
            fee_amount: Amount due
            due_date: Due date of the payment
            days_overdue: Number of days the payment is overdue
            hostel_name: Name of the hostel (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Determine the type of reminder based on days_overdue
        if days_overdue > 0:
            subject = f"OVERDUE: Hostel Fee Payment - {days_overdue} days overdue"
            urgency = "urgent"
        elif days_overdue == 0:
            subject = "Hostel Fee Payment Due Today"
            urgency = "important"
        else:
            subject = "Upcoming Hostel Fee Payment Reminder"
            urgency = "normal"
        
        # Format due date
        formatted_due_date = due_date.strftime("%B %d, %Y") if isinstance(due_date, date) else due_date
        
        # Create HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4a6572; color: white; padding: 15px; text-align: center; }}
                .content {{ padding: 20px; border: 1px solid #ddd; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
                .amount {{ font-size: 24px; font-weight: bold; text-align: center; margin: 20px 0; }}
                .urgent {{ color: #d9534f; }}
                .important {{ color: #f0ad4e; }}
                .normal {{ color: #5bc0de; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #4a6572; color: white; 
                          text-decoration: none; border-radius: 5px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">                <div class="header">
                    <h2>Hostel Fee Payment Reminder</h2>
                    {f"<h3>{hostel_name}</h3>" if hostel_name else ""}
                </div>
                <div class="content">
                    <p>Dear {student_name},</p>
                    
                    <p class="{urgency}">
                        {"Your hostel fee payment is overdue by " + str(days_overdue) + " days." if days_overdue > 0 else
                         "Your hostel fee payment is due today." if days_overdue == 0 else
                         "This is a reminder about your upcoming hostel fee payment."}                    </p>
                    
                    <p><strong>Student ID:</strong> {student_id}</p>
                    <p><strong>Due Date:</strong> {formatted_due_date}</p>
                    {f"<p><strong>Hostel:</strong> {hostel_name}</p>" if hostel_name else ""}
                    
                    <div class="amount">
                        Amount Due: ${fee_amount}
                    </div>
                    
                    <p>Please ensure timely payment to avoid any penalties.</p>
                    
                    <p>If you have already made the payment, please disregard this reminder and we thank you for your promptness.</p>
                    
                    <p>For any queries related to your payment, please contact the hostel administration office.</p>
                    
                    <center>
                        <a href="#" class="button">View Payment Details</a>
                    </center>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Hostel Management System.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create plain text content
        text_content = f"""
        Hostel Fee Payment Reminder
        
        Dear {student_name},
        
        {"Your hostel fee payment is overdue by " + str(days_overdue) + " days." if days_overdue > 0 else
         "Your hostel fee payment is due today." if days_overdue == 0 else
         "This is a reminder about your upcoming hostel fee payment."}
          Student ID: {student_id}
        Due Date: {formatted_due_date}
        Amount Due: ${fee_amount}
        {f"Hostel: {hostel_name}" if hostel_name else ""}
        
        Please ensure timely payment to avoid any penalties.
        
        If you have already made the payment, please disregard this reminder and we thank you for your promptness.
        
        For any queries related to your payment, please contact the hostel administration office.
        
        This is an automated message from the Hostel Management System.
        """
          # Send the email
        return EmailNotifier.send_email(
            to_email=student_email,
            subject=subject,
            message_html=html_content,
            message_text=text_content
        )
    
    @staticmethod
    def send_bulk_fee_reminders(days_threshold=3, hostel_id=None):
        """
        Send reminders to students with pending fees that are due within the threshold days
        or already overdue
        
        Args:
            days_threshold: Number of days before due date to send reminder
            hostel_id: Optional hostel ID to filter reminders by hostel
            
        Returns:
            Dictionary with counts of emails sent, failed, and skipped
        """
        from models.db import get_db_connection
        
        conn = get_db_connection()
        today = date.today()
        upcoming_due_date = (today + timedelta(days=days_threshold)).isoformat()
        
        # Get pending fees that are either due soon or overdue
        query = """
            SELECT f.id, f.student_id, f.amount, f.due_date, 
                   s.name, s.email, s.student_id_number, h.name as hostel_name
            FROM fees f
            JOIN students s ON f.student_id = s.id
            LEFT JOIN hostels h ON f.hostel_id = h.id
            WHERE f.status = 'Pending'
              AND (f.due_date <= ? OR f.due_date <= ?)
              AND s.email IS NOT NULL
        """
        params = [today.isoformat(), upcoming_due_date]
        
        # Add hostel filtering if specified
        if hostel_id is not None:
            query += " AND f.hostel_id = ? AND s.hostel_id = ?"
            params.extend([hostel_id, hostel_id])
        
        pending_fees = conn.execute(query, tuple(params)).fetchall()
        conn.close()
        
        # Statistics for reporting
        results = {
            'total': len(pending_fees),
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Send emails
        for fee in pending_fees:
            if not fee['email']:
                results['skipped'] += 1
                continue
                
            # Calculate days overdue (negative means upcoming)
            due_date = date.fromisoformat(fee['due_date'])
            days_overdue = (today - due_date).days
            
            # Include hostel name in the reminder if available
            hostel_name = fee.get('hostel_name', '')
            
            # Send the reminder email
            success = EmailNotifier.send_fee_reminder(
                student_id=fee['student_id_number'] or fee['student_id'],
                student_name=fee['name'],
                student_email=fee['email'],
                fee_amount=fee['amount'],
                due_date=due_date,
                days_overdue=days_overdue,
                hostel_name=hostel_name
            )
            
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
        
        return results
