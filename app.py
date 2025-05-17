"""
Main application module for the Hostel Management System
"""
from flask import Flask, render_template
import os
from datetime import date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models
from models.db import init_db

# Import route blueprints
from routes.dashboard import dashboard_bp
from routes.students import student_bp
from routes.rooms import room_bp
from routes.fees import fee_bp
from routes.complaints import complaints
from routes.fee_api import fee_api_bp

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_very_secret_key")  # Get from env or use default

# Register blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(student_bp)
app.register_blueprint(room_bp)
app.register_blueprint(fee_bp)
app.register_blueprint(complaints)
app.register_blueprint(fee_api_bp)  # Register the fee API blueprint

# Initialize app-wide data
from datetime import datetime
from utils.fee_utils import update_overdue_fees

# Store last check time to avoid checking on every request
app.config['LAST_OVERDUE_CHECK'] = None

@app.before_request
def check_overdue_fees():
    """Check and update overdue fees periodically (once per hour)."""
    last_check_time = app.config.get('LAST_OVERDUE_CHECK')
    current_time = datetime.now()
    
    # Only check once per hour to avoid performance issues
    if not last_check_time or (current_time - last_check_time).total_seconds() > 3600:
        try:
            updated = update_overdue_fees()
            if updated > 0:
                print(f"Updated {updated} overdue fees")
        except Exception as e:
            print(f"Error updating overdue fees: {e}")
        finally:
            app.config['LAST_OVERDUE_CHECK'] = current_time

@app.context_processor
def inject_current_date():
    """Make current date available to all templates."""
    return {'current_date': date.today()}

@app.context_processor
def inject_utility_functions():
    """Make utility functions available to all templates."""
    from utils.date_utils import format_currency
    return {
        'format_currency': format_currency
    }

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('errors/500.html'), 500

# Initialize the database if it doesn't exist
if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hostel.db')):
    init_db()

if __name__ == "__main__":
    # Run the application in debug mode
    app.run(debug=True)
