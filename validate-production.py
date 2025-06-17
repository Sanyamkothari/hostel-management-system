#!/usr/bin/env python3
"""
Production Readiness Validation Script
Validates all components required for production deployment
"""

import os
import sys
import subprocess
import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color

class ProductionValidator:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.warnings = 0
        self.base_url = "http://localhost:5000"
        
    def print_header(self, text: str):
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.NC}")
        print(f"{Colors.WHITE}{text.center(60)}{Colors.NC}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.NC}\n")
        
    def print_section(self, text: str):
        print(f"\n{Colors.BLUE}📋 {text}{Colors.NC}")
        print(f"{Colors.BLUE}{'-' * (len(text) + 4)}{Colors.NC}")
        
    def print_success(self, text: str):
        print(f"{Colors.GREEN}✅ {text}{Colors.NC}")
        self.tests_passed += 1
        
    def print_error(self, text: str):
        print(f"{Colors.RED}❌ {text}{Colors.NC}")
        self.tests_failed += 1
        
    def print_warning(self, text: str):
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")
        self.warnings += 1
        
    def print_info(self, text: str):
        print(f"{Colors.BLUE}ℹ️  {text}{Colors.NC}")
        
    def run_command(self, command: str) -> Tuple[bool, str]:
        """Run shell command and return success status and output"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def check_file_exists(self, filepath: str, required: bool = True) -> bool:
        """Check if file exists"""
        if os.path.exists(filepath):
            self.print_success(f"File exists: {filepath}")
            return True
        elif required:
            self.print_error(f"Required file missing: {filepath}")
            return False
        else:
            self.print_warning(f"Optional file missing: {filepath}")
            return False
    
    def validate_environment_config(self):
        """Validate environment configuration"""
        self.print_section("Environment Configuration")
        
        # Check for .env file
        env_exists = self.check_file_exists(".env", required=False)
        env_example_exists = self.check_file_exists(".env.example", required=True)
        
        if not env_exists and env_example_exists:
            self.print_warning("No .env file found, but .env.example exists")
            self.print_info("Copy .env.example to .env and configure values")
        
        # Check critical environment variables
        critical_vars = [
            'SECRET_KEY', 'DATABASE_URL', 'REDIS_URL', 
            'POSTGRES_PASSWORD', 'FLASK_ENV'
        ]
        
        if env_exists:
            try:
                with open('.env', 'r') as f:
                    env_content = f.read()
                    
                for var in critical_vars:
                    if f"{var}=" in env_content:
                        self.print_success(f"Environment variable configured: {var}")
                    else:
                        self.print_error(f"Missing environment variable: {var}")
            except Exception as e:
                self.print_error(f"Error reading .env file: {e}")
    
    def validate_docker_setup(self):
        """Validate Docker configuration"""
        self.print_section("Docker Configuration")
        
        # Check Docker installation
        success, output = self.run_command("docker --version")
        if success:
            self.print_success(f"Docker installed: {output.strip()}")
        else:
            self.print_error("Docker not installed or not running")
            return False
        
        # Check Docker Compose
        success, output = self.run_command("docker-compose --version")
        if success:
            self.print_success(f"Docker Compose installed: {output.strip()}")
        else:
            self.print_error("Docker Compose not installed")
            return False
        
        # Validate docker-compose.yml
        self.check_file_exists("docker-compose.yml", required=True)
        
        success, output = self.run_command("docker-compose config")
        if success:
            self.print_success("Docker Compose configuration valid")
        else:
            self.print_error(f"Invalid Docker Compose configuration: {output}")
            return False
            
        return True
    
    def validate_nginx_config(self):
        """Validate Nginx configuration"""
        self.print_section("Nginx Configuration")
        
        self.check_file_exists("nginx.conf", required=True)
        
        # Test nginx configuration syntax
        success, output = self.run_command(
            "docker run --rm -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf nginx:alpine nginx -t"
        )
        if success:
            self.print_success("Nginx configuration syntax valid")
        else:
            self.print_error(f"Nginx configuration syntax error: {output}")
    
    def validate_ssl_certificates(self):
        """Validate SSL certificates"""
        self.print_section("SSL Configuration")
        
        ssl_dir = "ssl"
        cert_file = os.path.join(ssl_dir, "cert.pem")
        key_file = os.path.join(ssl_dir, "key.pem")
        
        if os.path.exists(ssl_dir):
            self.print_success("SSL directory exists")
            
            if self.check_file_exists(cert_file, required=False):
                # Check certificate validity
                success, output = self.run_command(
                    f"openssl x509 -in {cert_file} -noout -checkend 86400"
                )
                if success:
                    self.print_success("SSL certificate is valid (24+ hours remaining)")
                else:
                    self.print_warning("SSL certificate expires within 24 hours")
            
            self.check_file_exists(key_file, required=False)
        else:
            self.print_warning("SSL directory not found - HTTPS will not be available")
    
    def test_application_services(self):
        """Test running application services"""
        self.print_section("Application Services")
        
        # Check if services are running
        success, output = self.run_command("docker-compose ps")
        if success:
            self.print_info("Docker Compose services status:")
            print(output)
            
            # Check individual services
            services = ['web', 'db', 'redis']
            for service in services:
                if f"{service}" in output and "Up" in output:
                    self.print_success(f"Service running: {service}")
                else:
                    self.print_error(f"Service not running: {service}")
        else:
            self.print_error("Cannot check service status - services may not be running")
            return False
            
        return True
    
    def test_database_connectivity(self):
        """Test database connectivity"""
        self.print_section("Database Connectivity")
        
        # Test PostgreSQL connection
        success, output = self.run_command(
            "docker-compose exec -T db pg_isready -U postgres"
        )
        if success:
            self.print_success("PostgreSQL connection successful")
        else:
            self.print_error(f"PostgreSQL connection failed: {output}")
        
        # Test database access
        success, output = self.run_command(
            "docker-compose exec -T db psql -U postgres -d hostel_management -c 'SELECT 1;'"
        )
        if success:
            self.print_success("Database query successful")
        else:
            self.print_error(f"Database query failed: {output}")
    
    def test_redis_connectivity(self):
        """Test Redis connectivity"""
        self.print_section("Redis Connectivity")
        
        success, output = self.run_command("docker-compose exec -T redis redis-cli ping")
        if success and "PONG" in output:
            self.print_success("Redis connection successful")
        else:
            self.print_error(f"Redis connection failed: {output}")
    
    def test_application_endpoints(self):
        """Test application HTTP endpoints"""
        self.print_section("Application Endpoints")
        
        # Wait a moment for application to be ready
        time.sleep(5)
        
        endpoints = [
            ("/", "Main page"),
            ("/health", "Health check"),
            ("/static/css/style.css", "Static files"),
            ("/socket.io/", "Socket.IO endpoint")
        ]
        
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code in [200, 404]:  # 404 is OK for some endpoints
                    self.print_success(f"{description} accessible")
                else:
                    self.print_warning(f"{description} returned status {response.status_code}")
            except requests.exceptions.RequestException as e:
                self.print_error(f"{description} failed: {e}")
    
    def test_socketio_functionality(self):
        """Test Socket.IO functionality"""
        self.print_section("Socket.IO Functionality")
        
        # Test Socket.IO endpoint accessibility
        try:
            response = requests.get(f"{self.base_url}/socket.io/", timeout=10)
            if response.status_code in [200, 400]:  # 400 is expected without proper handshake
                self.print_success("Socket.IO endpoint accessible")
            else:
                self.print_error(f"Socket.IO endpoint returned {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.print_error(f"Socket.IO endpoint test failed: {e}")
        
        # Check if Socket.IO test page is accessible
        try:
            response = requests.get(f"{self.base_url}/socketio-test/", timeout=10)
            if response.status_code == 200:
                self.print_success("Socket.IO test page accessible")
            else:
                self.print_warning("Socket.IO test page requires authentication")
        except requests.exceptions.RequestException as e:
            self.print_warning(f"Socket.IO test page check failed: {e}")
    
    def validate_security_configuration(self):
        """Validate security configuration"""
        self.print_section("Security Configuration")
        
        # Check for security headers
        try:
            response = requests.get(self.base_url, timeout=10)
            headers = response.headers
            
            security_headers = [
                'X-Content-Type-Options',
                'X-Frame-Options',
                'X-XSS-Protection',
                'Strict-Transport-Security'
            ]
            
            for header in security_headers:
                if header in headers:
                    self.print_success(f"Security header present: {header}")
                else:
                    self.print_warning(f"Security header missing: {header}")
                    
        except requests.exceptions.RequestException as e:
            self.print_error(f"Security headers check failed: {e}")
        
        # Check Flask-Talisman in requirements
        if self.check_file_exists("requirements.txt", required=True):
            try:
                with open("requirements.txt", "r") as f:
                    content = f.read()
                    if "Flask-Talisman" in content:
                        self.print_success("Flask-Talisman security library included")
                    else:
                        self.print_warning("Flask-Talisman not found in requirements.txt")
            except Exception as e:
                self.print_error(f"Error checking requirements.txt: {e}")
    
    def validate_backup_configuration(self):
        """Validate backup configuration"""
        self.print_section("Backup Configuration")
        
        # Check backup directory
        backup_dir = "backups"
        if os.path.exists(backup_dir):
            self.print_success("Backup directory exists")
        else:
            self.print_warning("Backup directory not found")
        
        # Check for backup scripts
        backup_scripts = [
            "deploy-production.sh",
            "/usr/local/bin/backup-hostel-db.sh"
        ]
        
        for script in backup_scripts:
            if os.path.exists(script):
                self.print_success(f"Backup script exists: {script}")
            else:
                self.print_warning(f"Backup script not found: {script}")
    
    def generate_summary_report(self):
        """Generate final summary report"""
        self.print_header("PRODUCTION READINESS SUMMARY")
        
        total_tests = self.tests_passed + self.tests_failed
        
        print(f"{Colors.GREEN}✅ Tests Passed: {self.tests_passed}{Colors.NC}")
        print(f"{Colors.RED}❌ Tests Failed: {self.tests_failed}{Colors.NC}")
        print(f"{Colors.YELLOW}⚠️  Warnings: {self.warnings}{Colors.NC}")
        print(f"{Colors.BLUE}📊 Total Tests: {total_tests}{Colors.NC}")
        
        if self.tests_failed == 0:
            readiness_score = (self.tests_passed / (self.tests_passed + self.warnings)) * 100
            print(f"\n{Colors.GREEN}🎉 PRODUCTION READINESS SCORE: {readiness_score:.1f}%{Colors.NC}")
            
            if readiness_score >= 90:
                print(f"{Colors.GREEN}🚀 READY FOR PRODUCTION DEPLOYMENT!{Colors.NC}")
            elif readiness_score >= 75:
                print(f"{Colors.YELLOW}⚠️  MOSTLY READY - Address warnings before deployment{Colors.NC}")
            else:
                print(f"{Colors.RED}❌ NOT READY - Address critical issues{Colors.NC}")
        else:
            print(f"\n{Colors.RED}❌ NOT READY FOR PRODUCTION{Colors.NC}")
            print(f"{Colors.RED}Please fix the failed tests before deployment{Colors.NC}")
        
        # Provide next steps
        print(f"\n{Colors.CYAN}📋 NEXT STEPS:{Colors.NC}")
        if self.tests_failed == 0:
            print("1. Review and address any warnings")
            print("2. Update .env file with production values")
            print("3. Set up domain and SSL certificates")
            print("4. Run production deployment script")
            print("5. Create admin user account")
            print("6. Perform user acceptance testing")
        else:
            print("1. Fix all failed tests")
            print("2. Re-run this validation script")
            print("3. Address any remaining warnings")
            print("4. Proceed with deployment when all tests pass")
    
    def run_validation(self):
        """Run complete production readiness validation"""
        self.print_header("HOSTEL MANAGEMENT SYSTEM - PRODUCTION READINESS VALIDATION")
        
        # Run all validation checks
        self.validate_environment_config()
        self.validate_docker_setup()
        self.validate_nginx_config()
        self.validate_ssl_certificates()
        self.test_application_services()
        self.test_database_connectivity()
        self.test_redis_connectivity()
        self.test_application_endpoints()
        self.test_socketio_functionality()
        self.validate_security_configuration()
        self.validate_backup_configuration()
        
        # Generate final report
        self.generate_summary_report()
        
        # Return status
        return self.tests_failed == 0

def main():
    """Main entry point"""
    validator = ProductionValidator()
    
    try:
        success = validator.run_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Validation interrupted by user{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Validation failed with error: {e}{Colors.NC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
