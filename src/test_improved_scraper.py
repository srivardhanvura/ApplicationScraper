#!/usr/bin/env python3

import pandas as pd
import time
from improved_hourly_scraper import ImprovedJobScraper

def test_improved_scraper():
    """Test the improved scraper with a few companies"""
    
    # Test with 5 companies
    test_companies = pd.DataFrame([
        {'company': 'Amazon', 'website': 'https://www.amazon.jobs/content/en/job-categories/software-development'},
        {'company': 'Apple', 'website': 'https://jobs.apple.com/en-us/search'},
        {'company': 'Cisco', 'website': 'https://jobs.cisco.com/jobs/SearchJobs/'},
        {'company': 'LinkedIn', 'website': 'https://careers.linkedin.com/search'},
        {'company': 'Reddit', 'website': 'https://reddit.wd1.myworkdayjobs.com/en-US/RDDT'}
    ])
    
    test_companies.to_csv('test_improved.csv', sep='|', index=False)
    
    print("🧪 TESTING IMPROVED SCRAPER")
    print("="*40)
    print("✅ Time-based filtering: Last 7 days only")
    print("✅ Better job detection")
    print("✅ Enhanced filtering logic")
    print("✅ Date parsing capabilities")
    print()
    
    # Test different configurations
    configs = [
        {'max_jobs': 15, 'max_days': 7, 'description': 'Standard (7 days)'},
        {'max_jobs': 15, 'max_days': 30, 'description': 'Extended (30 days)'}
    ]
    
    for i, config in enumerate(configs, 1):
        print(f"Test {i}: {config['description']}")
        print("-" * 30)
        
        scraper = ImprovedJobScraper(
            max_jobs_per_company=config['max_jobs'],
            max_workers=4,
            timeout=8,
            max_days_old=config['max_days']
        )
        
        start_time = time.time()
        new_jobs = scraper.run_scraping_cycle('test_improved.csv')
        elapsed_time = time.time() - start_time
        
        print(f"Results:")
        print(f"  Time: {elapsed_time:.1f} seconds")
        print(f"  New jobs saved: {new_jobs}")
        print(f"  Jobs per minute: {(new_jobs/(elapsed_time/60)):.1f}")
        print(f"  Days filter: {config['max_days']} days")
        print()

def check_database_jobs():
    """Check what jobs are in the database"""
    import psycopg2
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'job_scraper'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            port=os.getenv('DB_PORT', '5432')
        )
        
        cursor = conn.cursor()
        
        # Count total jobs
        cursor.execute("SELECT COUNT(*) FROM jobs;")
        total_jobs = cursor.fetchone()[0]
        
        # Count jobs by company
        cursor.execute("""
            SELECT company_name, COUNT(*) as job_count 
            FROM jobs 
            GROUP BY company_name 
            ORDER BY job_count DESC 
            LIMIT 10;
        """)
        company_stats = cursor.fetchall()
        
        # Count recent jobs
        cursor.execute("""
            SELECT COUNT(*) 
            FROM jobs 
            WHERE scraped_date >= NOW() - INTERVAL '1 day';
        """)
        recent_jobs = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print("📊 DATABASE STATISTICS")
        print("=" * 30)
        print(f"Total jobs in database: {total_jobs}")
        print(f"Jobs from last 24 hours: {recent_jobs}")
        print()
        print("Top companies by job count:")
        for company, count in company_stats:
            print(f"  {company}: {count} jobs")
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    # Check current database state
    check_database_jobs()
    print()
    
    # Test improved scraper
    test_improved_scraper()
    
    print()
    # Check database after test
    check_database_jobs() 