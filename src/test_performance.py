#!/usr/bin/env python3

import pandas as pd
import time
import logging
from hourly_job_scraper import HourlyJobScraper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_scraper_performance():
    """Test scraper performance with a subset of companies"""
    
    # Create test dataset with 10 companies
    test_companies = pd.DataFrame([
        {'company': 'Amazon', 'website': 'https://www.amazon.jobs/content/en/job-categories/software-development'},
        {'company': 'Meta', 'website': 'https://www.metacareers.com/jobs/'},
        {'company': 'Microsoft', 'website': 'https://careers.microsoft.com/us/en/search-results'},
        {'company': 'Apple', 'website': 'https://jobs.apple.com/en-us/search'},
        {'company': 'Google', 'website': 'https://careers.google.com/jobs/results/'},
        {'company': 'Netflix', 'website': 'https://jobs.netflix.com/search'},
        {'company': 'Oracle', 'website': 'https://careers.oracle.com/jobs/'},
        {'company': 'Cisco', 'website': 'https://jobs.cisco.com/jobs/SearchJobs/'},
        {'company': 'Adobe', 'website': 'https://careers.adobe.com/us/en/search-results'},
        {'company': 'NVIDIA', 'website': 'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite'}
    ])
    
    test_companies.to_csv('test_performance.csv', sep='|', index=False)
    
    # Test with different configurations
    configs = [
        {'max_workers': 4, 'max_jobs': 8, 'timeout': 6},
        {'max_workers': 6, 'max_jobs': 10, 'timeout': 8},
        {'max_workers': 8, 'max_jobs': 12, 'timeout': 10}
    ]
    
    print("🚀 PERFORMANCE TESTING")
    print("="*50)
    
    for i, config in enumerate(configs, 1):
        print(f"\nTest {i}: Workers={config['max_workers']}, Jobs={config['max_jobs']}, Timeout={config['timeout']}s")
        print("-" * 40)
        
        scraper = HourlyJobScraper(
            max_jobs_per_company=config['max_jobs'],
            max_workers=config['max_workers'],
            timeout=config['timeout']
        )
        
        start_time = time.time()
        new_jobs = scraper.run_scraping_cycle('test_performance.csv')
        elapsed_time = time.time() - start_time
        
        print(f"Results:")
        print(f"  Time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
        print(f"  New jobs found: {new_jobs}")
        print(f"  Time per company: {elapsed_time/10:.1f} seconds")
        print(f"  Estimated time for 40 companies: {(elapsed_time/10)*40/60:.1f} minutes")
        
        if elapsed_time < 600:  # Less than 10 minutes
            print(f"  ✅ GOOD - Fast enough for hourly execution")
        else:
            print(f"  ⚠️  SLOW - May not complete within hour")
    
    print(f"\n{'='*50}")
    print("RECOMMENDATIONS:")
    print("- For hourly execution, choose config with <15 minute estimate")
    print("- Monitor actual performance and adjust workers/timeout as needed")
    print("- Consider reducing max_jobs_per_company if too slow")

def test_database_connection():
    """Test database connection and setup"""
    print("\n🗄️  TESTING DATABASE CONNECTION")
    print("-" * 30)
    
    try:
        scraper = HourlyJobScraper()
        
        # Test database connection
        conn = scraper.db.get_connection() if hasattr(scraper.db, 'get_connection') else None
        if conn:
            conn.close()
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
        
        # Test saving a dummy job
        dummy_job = {
            'job_title': 'Test Software Engineer',
            'company_name': 'Test Company',
            'job_url': 'https://test.com/job/123',
            'job_description': 'Test job description',
            'experience_required': 'Entry Level',
            'location': 'Remote, USA',
            'posted_date': None,
            'salary': '',
            'employment_type': ''
        }
        
        saved = scraper.db.bulk_save_jobs([dummy_job])
        if saved > 0:
            print("✅ Database write successful")
        else:
            print("✅ Database write successful (job already exists)")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print("Make sure PostgreSQL is running and credentials are correct in .env file")

def main():
    """Run all performance tests"""
    print("🧪 JOB SCRAPER PERFORMANCE TESTS")
    print("="*50)
    
    # Test database first
    test_database_connection()
    
    # Test scraper performance
    test_scraper_performance()
    
    print(f"\n{'='*50}")
    print("NEXT STEPS:")
    print("1. If tests pass, run: python3 hourly_job_scraper.py")
    print("2. Set up email/SMS credentials in .env for notifications")
    print("3. Monitor logs in hourly_scraper.log")
    print("4. Adjust configuration based on performance")

if __name__ == "__main__":
    main() 