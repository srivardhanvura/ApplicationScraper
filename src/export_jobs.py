#!/usr/bin/env python3
"""
Export unsent jobs to CSV format for easy viewing in Excel/Google Sheets
"""

import os
import csv
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

def export_jobs_to_csv(filename=None):
    """Export all unsent jobs to CSV"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"unsent_jobs_{timestamp}.csv"
    
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
               date_posted, job_url, created_at, raw_text
        FROM jobs 
        WHERE email_sent = FALSE 
        ORDER BY company_name, created_at DESC
        """
        
        cursor.execute(query)
        jobs = cursor.fetchall()
        
        if not jobs:
            print("🎉 No unsent jobs found!")
            return
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow([
                'Job Title', 'Company', 'Location', 'Experience Required',
                'Date Posted', 'Apply URL', 'Found Date', 'Job Description'
            ])
            
            # Data rows
            for job in jobs:
                writer.writerow([
                    job[0],  # job_title
                    job[1],  # company_name
                    job[2],  # location
                    job[3],  # experience_required
                    job[4] or 'Recently',  # date_posted
                    job[5],  # job_url
                    job[6].strftime('%Y-%m-%d %H:%M') if job[6] else '',  # created_at
                    (job[7] or '')[:500] + '...' if job[7] and len(job[7]) > 500 else job[7] or ''  # raw_text (truncated)
                ])
        
        print(f"✅ Exported {len(jobs)} jobs to: {filename}")
        print(f"📂 Open with Excel, Google Sheets, or any CSV viewer")
        
        # Show summary
        companies = {}
        for job in jobs:
            company = job[1]
            companies[company] = companies.get(company, 0) + 1
        
        print(f"\n📊 Summary:")
        print(f"   • Total jobs: {len(jobs)}")
        print(f"   • Companies: {len(companies)}")
        print(f"   • Top companies:")
        for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"     - {company}: {count} jobs")
        
        cursor.close()
        conn.close()
        
        return filename
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    export_jobs_to_csv() 