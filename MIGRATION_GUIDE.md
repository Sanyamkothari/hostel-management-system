# Hostel Management System - Migration Guide

This guide will help you transition from the legacy version of the Hostel Management System to the new modular, feature-rich blueprint-based architecture.

## Table of Contents
1. [Overview of Changes](#overview-of-changes)
2. [Migration Steps](#migration-steps)
3. [New Features Guide](#new-features-guide)
4. [Troubleshooting](#troubleshooting)

## Overview of Changes

The Hostel Management System has been significantly enhanced with:

- **Modular Blueprint Architecture**: Code organized into separate modules for improved maintainability
- **Enhanced Security**: Environment variable configuration and better error handling
- **Advanced Fee Management**: Calendar view, batch processing, and email reminders
- **Maintenance System**: Full complaint and maintenance request tracking
- **Export Functionality**: PDF and CSV exports for data portability
- **Performance Improvements**: Database optimizations and caching
- **Improved UI/UX**: Modern interface with better visualizations

## Migration Steps

### Step 1: Update Your Database
The new version includes schema changes. Run the database upgrade script:

```bash
python upgrade_db.py
```

### Step 2: Update Environment Variables
Copy the sample .env file and configure it for your installation:

```bash
# Hostel Management System environment variables
SECRET_KEY=your_very_secret_key_should_be_long_and_random
DATABASE_PATH=hostel.db
DEBUG=True

# Email configuration for notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
DEFAULT_SENDER=hostel@example.com
```

### Step 3: Install New Dependencies
Install the additional required packages:

```bash
pip install -r requirements.txt
```

### Step 4: Run with New Structure
Use the run.py script to start the application with the new blueprint structure:

```bash
python run.py --debug
```

### Step 1: Backup Your Data
Before proceeding with the upgrade, ensure you have a backup of your database:

```
python run.py --backup-db
```

This will create a `hostel.db.backup` file in your installation directory.

### Step 2: Upgrade Database Schema
Run the database upgrade script to update your schema:

```
python upgrade_db.py
```

This script will:
- Create a backup of your database
- Add new fields to the students table
- Create the student_details table
- Add necessary indexes and constraints
- Verify the changes were applied correctly

### Step 3: Start Using the New Application
You can now start using the new version of the application:

```
python run.py
```

The system will automatically use the new modular structure.

## New Features Guide

### Email Fee Reminders
The system can now send automatic email reminders for upcoming and overdue fees:

1. Configure email settings in the .env file
2. Use the "Send Reminders" button on the fees page
3. Emails will be sent to students with upcoming or overdue payments

### Maintenance Request Tracking
Track and manage maintenance requests and complaints:

1. Access via the "Maintenance" menu
2. Add new maintenance requests, assign priority, and track status
3. Link requests to specific rooms or common areas

### PDF/CSV Export
Export data to PDF or CSV format:

1. Use the "Export" dropdown on the fees and rooms pages
2. Choose between PDF (formatted reports) or CSV (data only)
3. Apply filters before exporting to customize the data

### Batch Fee Processing
Process fees for multiple students at once:

1. Use the "Batch Assign Fees" button on the fees page
2. Select students, fee amount, and due date
3. Optionally set up recurring fees

### Enhanced Dashboard
- **Visual Metrics**: Room occupancy charts and fee collection statistics
- **Quick Access**: Buttons for common tasks
- **Activity Feed**: Recent system activities at a glance

### Student Management
- **Card View**: Toggle between list and card views using the view switcher
- **Enhanced Profiles**: More comprehensive student information including:
  - Student ID tracking
  - Emergency contacts
  - Expected checkout dates
  - Profile photos
- **Timeline View**: Student history in a visual timeline

### Room Management
- **Grid/List Views**: Toggle between grid and list views
- **Visual Indicators**: Color-coded room status
- **Advanced Filtering**: Filter by status, capacity, and occupancy

### Fee Management
- **Calendar View**: Access from Fees > View Calendar
- **Batch Processing**: Add fees for multiple students at once
- **Payment Reminders**: Automatically identified overdue payments
- **Export Options**: Generate fee reports in different formats

### Reporting
- **Room Occupancy Reports**: Visual representation of hostel capacity usage
- **Fee Collection Reports**: Track pending and collected fees
- **Custom Filters**: Generate reports based on various criteria

## Troubleshooting

### Email Sending Issues
If emails are not sending:
- Verify your SMTP credentials in .env
- For Gmail, ensure you're using an App Password
- Check if your email provider blocks outgoing SMTP

### Database Errors
If you encounter database errors:
- Run `python upgrade_db.py --repair` to check and repair database integrity
- Restore from backup if needed with `python run.py --restore-db-backup`

### Missing Features
If you don't see new features:
- Ensure you're using app_new.py (via run.py) and not the legacy app.py
- Check if all templates were correctly copied to the templates directory

## Support

For additional help, consult the repository README or contact the system administrator.

### Database Issues
If you encounter database errors after migration:

1. Check if the upgrade script completed successfully
2. Restore from backup if necessary:
   ```
   copy hostel.db.backup hostel.db
   ```
3. Manually verify database schema:
   ```
   python -c "from models.db import get_db_connection; conn = get_db_connection(); print(conn.execute('SELECT sql FROM sqlite_master WHERE type=\"table\"').fetchall())"
   ```

### Missing Templates
If you encounter "Template not found" errors:

1. Verify that all template files are in the correct directories
2. Check template paths in the route handlers
3. Restart the application

### Route Not Found
If you encounter "404 Not Found" errors for features that should exist:

1. Make sure all blueprint registrations are properly set up in app_new.py
2. Check URL patterns in the blueprint route decorators

### Getting Help
For further assistance, refer to the README.md file or contact system administration.
