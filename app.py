"""
Main application module for the Hostel Management System
Multi-Hostel Version
"""
from flask import Flask, render_template, session, g, request, redirect, url_for, flash
import os
from datetime import date
from dotenv import load_dotenv
# from flask_socketio import SocketIO  # Temporarily disabled for debugging
from db_utils import get_db_connection # Import get_db_connection
from config import config # Import the config dictionary
from utils.logging_config import setup_logging # Import logging setup

# Load environment variables
load_dotenv()

# Determine the configuration name from FLASK_ENV or default to 'development'
config_name = os.environ.get('FLASK_ENV', 'development')

# Import models
from models.db import init_db

# Import route blueprints
from routes.dashboard import dashboard_bp
from routes.students import student_bp
from routes.rooms import room_bp
from routes.simple_rooms import simple_room_bp
from routes.fees import fee_bp
from routes.expenses import expense_bp
from routes.complaints import complaints
from routes.fee_api import fee_api_bp
from routes.auth import auth_bp
from routes.owner import owner_bp
from utils.user_utils import get_user_attribute # Moved import for get_user_attribute
from routes.health import health_bp  # Health check endpoints

# Create Flask application
app = Flask(__name__)
app.config.from_object(config[config_name]) # Load configuration

# Setup Logging
app_logger, security_logger = setup_logging(app)

# Configure security headers and HTTPS for production
if config_name == 'production':
    from flask_talisman import Talisman
      # Content Security Policy for Socket.IO and real-time features
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'font-src': ["'self'", "https://cdnjs.cloudflare.com"],
        'img-src': ["'self'", "data:", "https:"],
        'connect-src': ["'self'", "ws:", "wss:", "ws://hostels.k2architects.in", "wss://hostels.k2architects.in"],  # Allow WebSocket connections for Socket.IO
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"]
    }
      # Initialize Talisman with security headers
    Talisman(
        app,
        force_https=True,  # Force HTTPS in production
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 year
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src', 'style-src'],
        feature_policy={
            'camera': "'none'",
            'microphone': "'none'",
            'geolocation': "'none'",
            'payment': "'none'"
        },
        referrer_policy='strict-origin-when-cross-origin',
        permissions_policy={
            'camera': '()',
            'microphone': '()',
            'geolocation': '()',
            'payment': '()'
        }
    )
    app_logger.info("Production security headers configured with Flask-Talisman")
else:
    app_logger.info("Development mode - security headers disabled")

# Initialize WhiteNoise for serving static files in production
if not app.config.get("DEBUG"):
    from whitenoise import WhiteNoise
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(os.path.dirname(__file__), 'static'))
    # Add prefixes for any other static folders if they are not under the main 'static' root
    # For example, if you have static files directly under a blueprint's static folder that are not being served
    # app.wsgi_app.add_files(os.path.join(os.path.dirname(__file__), 'some_blueprint/static'), prefix='some_blueprint/static')


# Initialize SocketIO for real-time updates
from flask_socketio import SocketIO

# Configure message queue for production (Redis) if available
message_queue = None
if config_name == 'production' and app.config.get('SOCKETIO_MESSAGE_QUEUE'):
    message_queue = app.config.get('SOCKETIO_MESSAGE_QUEUE')
    app_logger.info(f"SocketIO configured with Redis message queue: {message_queue}")

socketio = SocketIO(
    app, 
    cors_allowed_origins=app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', "*"), # Use config value
    async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading'),  # Use config value
    logger=app_logger, # Use the configured app_logger
    engineio_logger=app_logger, # Use the configured app_logger
    message_queue=message_queue,  # Redis message queue for scaling
    ping_timeout=60,
    ping_interval=25
)

# Register Socket.IO event handlers
from socket_events import register_socket_events
register_socket_events(socketio)

# Register blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(student_bp)
app.register_blueprint(room_bp)
app.register_blueprint(simple_room_bp)  # Register the simple room management blueprint
app.register_blueprint(fee_bp)
app.register_blueprint(expense_bp)      # Register the expense management blueprint
app.register_blueprint(complaints)
app.register_blueprint(fee_api_bp)  # Register the fee API blueprint
app.register_blueprint(auth_bp)     # Register the authentication blueprint
app.register_blueprint(owner_bp)    # Register the owner dashboard blueprint
app.register_blueprint(health_bp)   # Register the health check blueprint

# Register Socket.IO test blueprint (only in development)
import os
if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEBUG') == 'True':
    from routes.socketio_test import socketio_test_bp
    from routes.socketio_monitor import socketio_monitor_bp
    app.register_blueprint(socketio_test_bp)
    app.register_blueprint(socketio_monitor_bp)

# Configure multi-hostel system
# app.config['MULTI_HOSTEL_ENABLED'] = True # This is already in Config class

# Initialize app-wide data
from datetime import datetime
from utils.fee_utils import update_overdue_fees

# Store last check time to avoid checking on every request
# app.config['LAST_OVERDUE_CHECK'] = None # This can be initialized if needed, or rely on .get default

@app.before_request
def load_user():
    """Load user data into g.user if user is logged in."""
    if 'user_id' in session:
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                if user:
                    g.user = dict(user)  # Convert SQLite Row to dict
                else:
                    g.user = None
            else:
                g.user = None
        except Exception as e:
            print(f"Error loading user: {e}")
            g.user = None
    else:
        g.user = None

@app.teardown_appcontext
def close_db(error):
    """Close database connection at the end of request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

# get_user_attribute function removed, now imported from utils.user_utils

# Make the helper function available in templates
app.jinja_env.globals.update(get_user_attribute=get_user_attribute) # Uses imported version

@app.before_request
def check_overdue_fees():
    """Check and update overdue fees periodically (once per hour)."""
    # Skip for authentication routes and static files
    if request.endpoint in ['auth.login', 'static']:
        return
        
    # Only proceed if user is authenticated
    if not g.user:
        if request.endpoint != 'auth.login':
            return redirect(url_for('auth.login'))
        return
    
    last_check_time = app.config.get('LAST_OVERDUE_CHECK')
    current_time = datetime.now()
    
    # Only check once per hour to avoid performance issues
    if not last_check_time or (current_time - last_check_time).total_seconds() > 3600:
        try:
            updated = update_overdue_fees()
            if updated > 0:
                app_logger.info(f"Updated {updated} overdue fees")
                # Emit a socket.io event for real-time notification
                socketio.emit('fees_updated', {'count': updated}, namespace='/updates')
        except Exception as e:
            app_logger.error(f"Error updating overdue fees: {e}")
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

@app.route('/')
def index():
    """Main index route - redirect to dashboard"""
    return redirect(url_for('dashboard.index'))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('errors/500.html'), 500

if __name__ == "__main__":
    # Create migrations directory if it doesn't exist
    migrations_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations')
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)
    
    # Initialize the database if it doesn't exist
    # Use database URL from config
    db_url = app.config.get('DATABASE_URL', 'sqlite:///hostel.db')
    db_path_from_url = db_url.replace('sqlite:///', '') # Basic parsing for sqlite
    
    # Ensure db_path is absolute if it's a relative path for SQLite
    if db_url.startswith('sqlite:///') and not os.path.isabs(db_path_from_url):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path_from_url)
    else:
        db_path = db_path_from_url

    if db_url.startswith('sqlite:///') and not os.path.exists(db_path):
        init_db()
        
        # Import and run migration if database was just created
        from migrations.migrate import run_migration
        run_migration()    # Apply hostel filters
    from utils.auth_utils import apply_hostel_filters
    apply_hostel_filters()
      # Run the application with SocketIO for real-time updates
    app_logger.info(f"Starting Flask-SocketIO server with {config_name} configuration...")
    
    # Use appropriate host and port for production vs development
    if config_name == 'production':
        # Production: bind to all interfaces, use environment port or default
        host = '0.0.0.0'
        port = int(os.environ.get('PORT', 5000))
        debug = False
    else:
        # Development: localhost only
        host = '127.0.0.1'
        port = 5000
        debug = True
    
    socketio.run(app, debug=debug, host=host, port=port)
