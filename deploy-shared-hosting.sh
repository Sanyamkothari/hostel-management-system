#!/bin/bash
# Production Deployment Script for Shared Hosting

echo "🚀 Starting Hostel Management System Deployment..."

# Create necessary directories
mkdir -p logs
mkdir -p migrations

# Set proper permissions
chmod 755 app.py
chmod 755 static/
chmod 755 templates/
chmod 644 requirements.txt

# Install Python dependencies (if pip is available)
if command -v pip3 &> /dev/null; then
    echo "📦 Installing Python dependencies..."
    pip3 install --user -r requirements.txt
else
    echo "⚠️  Please install Python dependencies manually"
fi

# Copy environment configuration
if [ ! -f .env ]; then
    cp .env.production.template .env
    echo "📝 Created .env file - please edit with your actual values"
else
    echo "✅ .env file already exists"
fi

# Set up database (if running for first time)
echo "🗄️  Initializing database..."
python3 -c "
import os
os.environ['FLASK_ENV'] = 'production'
from models.db import init_db
from migrations.migrate import run_migration
init_db()
run_migration()
print('Database initialized successfully')
"

echo "✅ Deployment preparation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your actual database and Redis URLs"
echo "2. Configure your web server to serve the application"
echo "3. Set up SSL certificate"
echo "4. Create user accounts for owner and managers"
