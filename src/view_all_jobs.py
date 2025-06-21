#!/usr/bin/env python3
"""
Quick script to view all unsent jobs from the database
Run this to see ALL jobs that were found but not yet sent in email
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime

# Load environment variables
load_dotenv()

def view_all_unsent_jobs():
    """View all unsent jobs in a readable format"""
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
        
        # Get all unsent jobs
        query = """
        SELECT job_title, company_name, location, experience_required, 
               date_posted, job_url, created_at
        FROM jobs 
        WHERE email_sent = FALSE 
        ORDER BY created_at DESC, company_name
        """
        
        cursor.execute(query)
        jobs = cursor.fetchall()
        
        if not jobs:
            print("🎉 No unsent jobs found! All jobs have been notified.")
            return
        
        print(f"\n📧 {len(jobs)} UNSENT JOBS FOUND:\n")
        print("=" * 100)
        
        current_company = None
        company_count = 0
        
        for i, job in enumerate(jobs, 1):
            job_title, company_name, location, experience, date_posted, job_url, created_at = job
            
            # Group by company
            if company_name != current_company:
                if current_company is not None:
                    print()
                print(f"\n🏢 {company_name.upper()} ({company_count} jobs)")
                print("-" * 50)
                current_company = company_name
                company_count = 0
            
            company_count += 1
            
            print(f"{i:2d}. {job_title}")
            print(f"    📍 Location: {location}")
            print(f"    🎯 Experience: {experience}")
            print(f"    📅 Posted: {date_posted or 'Recently'}")
            print(f"    🔗 Apply: {job_url}")
            print(f"    ⏰ Found: {created_at.strftime('%Y-%m-%d %H:%M')}")
            print()
        
        print("=" * 100)
        print(f"\n💡 SUMMARY:")
        print(f"   • Total unsent jobs: {len(jobs)}")
        
        # Count by company
        companies = {}
        for job in jobs:
            company = job[1]
            companies[company] = companies.get(company, 0) + 1
        
        print(f"   • Companies with jobs: {len(companies)}")
        print(f"   • Top companies:")
        for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"     - {company}: {count} jobs")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("Make sure your .env file is configured correctly.")

def mark_all_as_sent():
    """Mark all current unsent jobs as sent (if you want to clear the queue)"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'job_scraper'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            port=os.getenv('DB_PORT', '5432')
        )
        
        cursor = conn.cursor()
        
        # Count unsent jobs
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE email_sent = FALSE")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("No unsent jobs to mark.")
            return
        
        # Ask for confirmation
        response = input(f"\n⚠️  Mark {count} unsent jobs as sent? (y/N): ").lower()
        if response != 'y':
            print("Cancelled.")
            return
        
        # Mark as sent
        cursor.execute("UPDATE jobs SET email_sent = TRUE WHERE email_sent = FALSE")
        conn.commit()
        
        print(f"✅ Marked {count} jobs as sent.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mark-sent":
        mark_all_as_sent()
    else:
        view_all_unsent_jobs()
        print("\n💡 To mark all jobs as sent: python3 view_all_jobs.py --mark-sent") 