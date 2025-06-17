# Hostel Management System - Deployment Guide

## 🎯 Quick Deployment Steps

### 1. Cloud Services Setup (Free Tiers)

**PostgreSQL Database (ElephantSQL - Free):**
1. Go to https://www.elephantsql.com/
2. Sign up for free account
3. Create a new database instance (Tiny Turtle - Free)
4. Note down the connection URL

**Redis (Redis Cloud - Free):**
1. Go to https://redis.com/try-free/
2. Sign up for free account  
3. Create a new database (30MB free)
4. Note down the Redis URL

### 2. Domain Configuration

**DNS Setup:**
```
Type: A Record
Name: hostel
Value: [Your Server IP]
TTL: 3600
```

**Result:** hostel.yourdomain.com → Your Application

### 3. Server Setup

**Upload files to your hosting:**
```bash
# Upload all project files to your hosting directory
# Usually: /public_html/hostel/ or similar
```

**Install dependencies:**
```bash
pip install --user -r requirements.txt
```

### 4. Configuration

**Edit .env file:**
```bash
cp .env.production.template .env
nano .env
```

Fill in your actual values:
- DATABASE_URL (from ElephantSQL)
- REDIS_URL (from Redis Cloud)
- SECRET_KEY (generate a secure one)
- DOMAIN_NAME (your subdomain)

### 5. Database Initialization

```bash
python3 -c "
import os
os.environ['FLASK_ENV'] = 'production'
from models.db import init_db
from migrations.migrate import run_migration
init_db()
run_migration()
"
```

### 6. Web Server Configuration

**For Apache (.htaccess):**
```apache
RewriteEngine On
RewriteCond %{REQUEST_URI} !^/hostel/
RewriteRule ^(.*)$ /hostel/$1 [L]
```

**For Nginx:**
```nginx
location /hostel/ {
    proxy_pass http://127.0.0.1:5000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### 7. SSL Setup (Let's Encrypt)

```bash
# Most shared hosting providers offer free SSL
# Enable it in your hosting control panel
```

### 8. Create User Accounts

```bash
python3 -c "
from utils.auth_utils import create_initial_users
create_initial_users()
"
```

### 9. Start Application

```bash
python3 wsgi.py
```

## 🔧 Troubleshooting

**Common Issues:**
1. **Port access**: Use hosting control panel to configure port forwarding
2. **Python version**: Ensure Python 3.8+ is available
3. **Database connection**: Verify DATABASE_URL is correct
4. **SSL errors**: Ensure certificate is properly configured

## 📱 Access Instructions

**For Owner and Managers:**
1. Open web browser
2. Go to: https://hostel.yourdomain.com
3. Login with provided credentials
4. Real-time updates work automatically

## 🔐 Security Checklist

- ✅ Change default SECRET_KEY
- ✅ Use HTTPS only
- ✅ Restrict database access
- ✅ Regular backups enabled
- ✅ Monitor access logs

## 📊 Monitoring

**Health Check URL:** https://hostel.yourdomain.com/health

**Log Files:**
- Application: `logs/hostel_management.log`
- Security: `logs/security.log`
