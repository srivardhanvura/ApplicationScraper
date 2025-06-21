import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (not specific database)
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            port=os.getenv('DB_PORT', '5432'),
            dbname='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        db_name = os.getenv('DB_NAME', 'job_scraper')
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        return False
    
    return True

def setup_tables():
    """Setup database tables and indexes"""
    try:
        # Connect to the job_scraper database
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'job_scraper'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            port=os.getenv('DB_PORT', '5432')
        )
        cursor = conn.cursor()
        
        # Create jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                job_title VARCHAR(500) NOT NULL,
                company_name VARCHAR(200) NOT NULL,
                job_url VARCHAR(1000) UNIQUE NOT NULL,
                job_description TEXT,
                experience_required VARCHAR(100),
                location VARCHAR(200),
                posted_date TIMESTAMP,
                salary VARCHAR(200),
                employment_type VARCHAR(100),
                scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notification_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(job_url);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_notification ON jobs(notification_sent);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_scraped_date ON jobs(scraped_date);
        """)
        
        # Create companies table for tracking scraping statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                company_name VARCHAR(200) UNIQUE NOT NULL,
                website_url VARCHAR(1000),
                last_scraped TIMESTAMP,
                total_jobs_found INTEGER DEFAULT 0,
                entry_level_jobs_found INTEGER DEFAULT 0,
                scraping_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create scraping_logs table for monitoring
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraping_logs (
                id SERIAL PRIMARY KEY,
                company_name VARCHAR(200),
                scrape_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                jobs_found INTEGER DEFAULT 0,
                entry_level_found INTEGER DEFAULT 0,
                status VARCHAR(50),
                error_message TEXT,
                duration_seconds INTEGER
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("Database tables and indexes created successfully")
        return True
        
    except Exception as e:
        print(f"Error setting up tables: {e}")
        return False

def main():
    """Main setup function"""
    print("Setting up job scraper database...")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Error: .env file not found. Please create one based on .env.template")
        return False
    
    # Create database
    if not create_database():
        return False
    
    # Setup tables
    if not setup_tables():
        return False
    
    print("Database setup completed successfully!")
    print("\nNext steps:")
    print("1. Make sure your .env file has correct database credentials")
    print("2. Configure email and SMS settings in .env")
    print("3. Run the web scraper: python web_scraper.py")
    
    return True

if __name__ == "__main__":
    main() 