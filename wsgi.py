from app import app, socketio

# WSGI entry point for production servers
if __name__ == "__main__":
    # For production, use a proper WSGI server like Gunicorn
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
else:
    # For WSGI servers
    application = app
