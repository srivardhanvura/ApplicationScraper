#!/usr/bin/env python3

import os
import subprocess
import sys

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    else:
        print(f"✅ Python {sys.version.split()[0]} is compatible")

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        print("Try running manually: pip install -r requirements.txt")
        return False
    return True

def check_postgresql():
    """Check if PostgreSQL is available"""
    print("\n🗄️  Checking PostgreSQL...")
    try:
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ PostgreSQL found: {result.stdout.strip()}")
            return True
        else:
            print("❌ PostgreSQL not found")
            return False
    except FileNotFoundError:
        print("❌ PostgreSQL not found in PATH")
        return False

def setup_environment():
    """Setup environment file"""
    print("\n⚙️  Setting up environment...")
    
    if not os.path.exists('.env'):
        if os.path.exists('env_template.txt'):
            print("Creating .env file from template...")
            with open('env_template.txt', 'r') as template:
                content = template.read()
            with open('.env', 'w') as env_file:
                env_file.write(content)
            print("✅ .env file created")
            print("⚠️  Please edit .env file with your actual credentials")
        else:
            print("❌ env_template.txt not found")
            return False
    else:
        print("✅ .env file already exists")
    
    return True

def create_database():
    """Create database if it doesn't exist"""
    print("\n🏗️  Setting up database...")
    
    # Try to create database
    try:
        # Check if database exists
        result = subprocess.run([
            'psql', '-h', 'localhost', '-U', 'postgres', 
            '-lqt'], capture_output=True, text=True, input='')
        
        if 'job_scraper' in result.stdout:
            print("✅ Database 'job_scraper' already exists")
        else:
            # Create database
            subprocess.run([
                'psql', '-h', 'localhost', '-U', 'postgres', 
                '-c', 'CREATE DATABASE job_scraper;'], check=True)
            print("✅ Database 'job_scraper' created")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Database setup failed: {e}")
        print("Please create database manually:")
        print("  psql -U postgres -c 'CREATE DATABASE job_scraper;'")
        return False

def run_tests():
    """Run basic tests to verify setup"""
    print("\n🧪 Running basic tests...")
    
    try:
        # Test import
        from hourly_job_scraper import HourlyJobScraper
        print("✅ Import test passed")
        
        # Test database connection
        scraper = HourlyJobScraper()
        print("✅ Database connection test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 JOB SCRAPER SETUP")
    print("="*40)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    if not install_dependencies():
        return
    
    # Check PostgreSQL
    postgres_ok = check_postgresql()
    
    # Setup environment
    if not setup_environment():
        return
    
    # Setup database (if PostgreSQL is available)
    if postgres_ok:
        create_database()
    else:
        print("\n⚠️  PostgreSQL setup skipped. Please install PostgreSQL and create 'job_scraper' database manually.")
    
    # Run tests
    if postgres_ok:
        run_tests()
    
    print("\n" + "="*40)
    print("🎉 SETUP COMPLETE!")
    print("\nNext steps:")
    print("1. Edit .env file with your credentials")
    print("2. Make sure PostgreSQL is running")
    print("3. Run: python3 test_performance.py")
    print("4. If tests pass, run: python3 hourly_job_scraper.py")
    print("\nFor help, check README.md")

if __name__ == "__main__":
    main() 