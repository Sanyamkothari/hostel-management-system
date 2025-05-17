# Hostel Management System

A comprehensive system for managing hostel operations including student registrations, room assignments, fee collection, and reporting.

## Features

- **Student Management**: Register students, assign rooms, track personal details
- **Room Management**: Track room availability, occupancy, and maintenance status
- **Fee Management**: Collect and track hostel fees, generate payment receipts
- **Advanced Dashboards**: Visual representations of room occupancy and fee status
- **Reporting**: Generate reports on occupancy, fee collection, and student status

## Recent Improvements

### Database Optimization
- Added missing columns (student_id_number, expected_checkout_date)
- Improved database schema for better relationships and constraints

### Code Reorganization
- Modular architecture with separate directories for:
  - **models**: Database operations and data models
  - **routes**: Controller logic and route handlers
  - **utils**: Utility functions and helpers
  - **templates**: View templates organized by feature
  - **static**: CSS, JavaScript, and other static assets

### UI/UX Enhancements
- **Dashboard**: Interactive charts, metric cards, recent activity feed
- **Student Management**: Card view for students with profile photos
- **Room Visualization**: Interactive grid/list views with occupancy indicators
- **Fee Management**: Calendar view, batch processing, payment reminders

### New Features
- **Enhanced Student Profiles**: Detailed student information with history tracking
- **Advanced Fee Management**: Calendar view, batch payments, reminders system
- **Improved Search & Filtering**: Real-time filtering across all modules
- **Reporting System**: Print functionality, data export options

## Project Structure

```
hostel_management_v2/
├── app.py                 # Main application file (legacy)
├── app_new.py             # New modular application entrypoint
├── run.py                 # Script to run the application
├── models/                # Database models
│   └── db.py              # Database operations
├── routes/                # Route handlers
│   ├── dashboard.py       # Dashboard routes
│   ├── students.py        # Student management routes
│   ├── rooms.py           # Room management routes
│   └── fees.py            # Fee management routes
├── utils/                 # Utility functions
│   ├── date_utils.py      # Date handling utilities
│   ├── file_handlers.py   # File upload handlers
│   ├── general.py         # General utilities
│   └── validators.py      # Input validation
├── static/                # Static assets
│   ├── css/               # CSS files
│   └── js/                # JavaScript files
└── templates/             # HTML templates
    ├── errors/            # Error pages
    ├── students/          # Student templates
    ├── rooms/             # Room templates
    ├── fees/              # Fee templates
    └── reports/           # Report templates
```

## Running the Application

### Prerequisites
- Python 3.7+
- SQLite3

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python run.py`

### Switching to New Architecture

The new modular architecture can be used by running:

```
python run.py --debug
```

The legacy version can still be run with:

```
python app.py
```

## Upgrading from Previous Version

If you're upgrading from an earlier version:

1. Back up your database:
```
python run.py --backup-db
```

2. Run the upgrade script:
```
python upgrade_db.py
```

3. For detailed instructions, see the [Migration Guide](MIGRATION_GUIDE.md).

## Testing

Run the system test script to verify all components:

```
python system_test.py
```

This will check:
- Database connections and schema
- Model classes functionality
- Route modules registration
- Template and static file presence

## API Documentation

### Student API

- `GET /students/` - List all students
- `POST /students/add` - Add a new student
- `GET /students/<id>` - View student details
- `POST /students/edit/<id>` - Update student information
- `POST /students/delete/<id>` - Delete a student

### Room API

- `GET /rooms/` - List all rooms
- `POST /rooms/add` - Add a new room
- `GET /rooms/<id>` - View room details
- `POST /rooms/edit/<id>` - Update room information
- `POST /rooms/delete/<id>` - Delete a room

### Fee API

- `GET /fees/` - List all fees
- `POST /fees/add` - Add a new fee
- `GET /fees/calendar` - View fee calendar
- `POST /fees/batch` - Process batch payments
- `POST /fees/edit/<id>` - Update fee information
- `POST /fees/delete/<id>` - Delete a fee

## Future Improvements

- Mobile-responsive design for all pages
- Full-text search for students and records
- Advanced security features (user roles, permissions)
- API endpoints for integration with other systems
- Email notifications for fee reminders
