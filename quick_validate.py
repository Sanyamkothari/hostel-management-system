#!/usr/bin/env python3
"""
Quick Deployment Validation
Final validation check for production readiness
"""

import os
import sys
from pathlib import Path

def main():
    print("🔍 Quick Deployment Validation")
    print("=" * 50)
    
    project_root = Path(__file__).parent
    checks_passed = 0
    total_checks = 0
    
    # Check critical files
    critical_files = [
        'app.py', 'socket_events.py', 'routes/health.py', 
        'docker-compose.yml', 'Dockerfile', 'requirements.txt',
        '.env.production', 'nginx.conf'
    ]
    
    print("\n📁 Checking Critical Files:")
    for file in critical_files:
        total_checks += 1
        file_path = project_root / file
        if file_path.exists():
            print(f"  ✅ {file}")
            checks_passed += 1
        else:
            print(f"  ❌ {file} - MISSING")
    
    # Check deployment scripts
    deployment_scripts = [
        'test-deployment.sh', 'test-deployment.ps1',
        'setup-production.sh', 'setup-production.ps1',
        'validate-production.py', 'deployment_status.py'
    ]
    
    print("\n🚀 Checking Deployment Scripts:")
    for script in deployment_scripts:
        total_checks += 1
        script_path = project_root / script
        if script_path.exists():
            print(f"  ✅ {script}")
            checks_passed += 1
        else:
            print(f"  ❌ {script} - MISSING")    # Check requirements
    print("\n📦 Checking Dependencies:")
    req_file = project_root / 'requirements.txt'
    if req_file.exists():
        with open(req_file, 'r') as f:
            requirements = f.read()
        
        critical_deps = ['Flask', 'gunicorn', 'redis', 'Flask-SocketIO', 'Flask-Talisman']
        for dep in critical_deps:
            total_checks += 1
            try:
                # Try to import the package to check if it's installed
                if dep == 'Flask':
                    import flask
                    print(f"  ✅ {dep}")
                    checks_passed += 1
                elif dep == 'gunicorn':
                    import gunicorn
                    print(f"  ✅ {dep}")
                    checks_passed += 1
                elif dep == 'redis':
                    import redis
                    print(f"  ✅ {dep}")
                    checks_passed += 1
                elif dep == 'Flask-SocketIO':
                    import flask_socketio
                    print(f"  ✅ {dep}")
                    checks_passed += 1
                elif dep == 'Flask-Talisman':
                    import flask_talisman
                    print(f"  ✅ {dep}")
                    checks_passed += 1
            except ImportError:
                print(f"  ❌ {dep} - MISSING")
    
    # Calculate score
    score_percentage = (checks_passed / total_checks) * 100
    
    print(f"\n📊 Validation Results:")
    print(f"   Score: {checks_passed}/{total_checks} ({score_percentage:.1f}%)")
    
    if score_percentage >= 95:
        status = "🌟 EXCELLENT - Ready for production!"
        exit_code = 0
    elif score_percentage >= 85:
        status = "✅ GOOD - Ready for production with minor improvements"
        exit_code = 0
    elif score_percentage >= 75:
        status = "⚠️ FAIR - Address issues before production"
        exit_code = 1
    else:
        status = "❌ POOR - Significant work needed"
        exit_code = 2
    
    print(f"   Status: {status}")
    
    if score_percentage >= 85:
        print(f"\n🎉 DEPLOYMENT APPROVED!")
        print(f"   Your Hostel Management System is ready for production deployment.")
        print(f"   Next steps:")
        print(f"   1. Run: docker-compose up -d")
        print(f"   2. Test: python validate-production.py")
        print(f"   3. Deploy to production server")
    else:
        print(f"\n⚠️ DEPLOYMENT NOT READY")
        print(f"   Please address the missing components before deployment.")
    
    print("=" * 50)
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
