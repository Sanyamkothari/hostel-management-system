"""
Configuration Helper for Production Deployment
Updates CSP and CORS settings for your subdomain
"""
import os
import re

def update_domain_config(domain_name):
    """Update domain-specific configuration in app.py"""
    
    app_file = 'app.py'
    
    # Read the current app.py file
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Update CSP connect-src to include your domain
    csp_pattern = r"'connect-src': \[\"'self'\", \"ws:\", \"wss:\"\]"
    new_csp = f"'connect-src': [\"'self'\", \"ws:\", \"wss:\", \"ws://{domain_name}\", \"wss://{domain_name}\"]"
    
    content = re.sub(csp_pattern, new_csp, content)
    
    # Write back the updated content
    with open(app_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated CSP configuration for domain: {domain_name}")

def update_config_file(domain_name):
    """Update config.py with domain-specific settings"""
    
    config_file = 'config.py'
    
    # Read the current config.py file
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Update SOCKETIO_CORS_ALLOWED_ORIGINS
    cors_pattern = r'SOCKETIO_CORS_ALLOWED_ORIGINS = "\*"'
    new_cors = f'SOCKETIO_CORS_ALLOWED_ORIGINS = os.environ.get("SOCKETIO_CORS_ALLOWED_ORIGINS", "https://{domain_name}")'
    
    content = re.sub(cors_pattern, new_cors, content)
    
    # Write back the updated content
    with open(config_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated CORS configuration for domain: {domain_name}")

if __name__ == "__main__":
    domain = "hostel.k2architects.in"  # Your domain
    
    if domain:
        update_domain_config(domain)
        update_config_file(domain)
        print(f"\n🎉 Configuration updated for {domain}")
        print("Don't forget to update your .env file with the same domain!")
    else:
        print("❌ No domain provided")
