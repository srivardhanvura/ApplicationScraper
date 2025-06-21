#!/usr/bin/env python3

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_database_schema():
    """Update database schema to add new columns"""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'job_scraper'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            port=os.getenv('DB_PORT', '5432')
        )
        
        cursor = conn.cursor()
        
        # Add new columns if they don't exist
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS date_posted VARCHAR(100);")
            print("✅ Added date_posted column")
        except Exception as e:
            print(f"date_posted column: {e}")
        
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS raw_text TEXT;")
            print("✅ Added raw_text column")
        except Exception as e:
            print(f"raw_text column: {e}")
        
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS email_sent BOOLEAN DEFAULT FALSE;")
            print("✅ Added email_sent column")
        except Exception as e:
            print(f"email_sent column: {e}")
        
        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Database schema updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating database schema: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Updating database schema for improved scraper...")
    success = update_database_schema()
    
    if success:
        print("\n🎉 Database is ready for the improved scraper!")
        print("You can now run: python3 improved_hourly_scraper.py")
    else:
        print("\n❌ Database update failed. Please check your database connection.") 