import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import psycopg2
from psycopg2.extras import execute_values
import re
import time
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import schedule
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import csv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('improved_scraper.log'),
        logging.StreamHandler()
    ]
)

class JobDatabase:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'job_scraper'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'port': os.getenv('DB_PORT', '5432')
        }
        self.setup_database()
    
    def setup_database(self):
        """Setup database and tables"""
        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_posted VARCHAR(100),
                    raw_text TEXT
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(job_url);
                CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
                CREATE INDEX IF NOT EXISTS idx_jobs_notification ON jobs(notification_sent);
                CREATE INDEX IF NOT EXISTS idx_jobs_scraped_date ON jobs(scraped_date);
                CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date);
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logging.error(f"Database setup error: {e}")
    
    def bulk_save_jobs(self, jobs_list):
        """Save jobs in bulk with conflict handling"""
        if not jobs_list:
            return 0
        
        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO jobs (job_title, company_name, job_url, job_description, 
                                experience_required, location, posted_date, salary, employment_type,
                                date_posted, raw_text)
                VALUES %s
                ON CONFLICT (job_url) DO NOTHING
                RETURNING id
            """
            
            values = []
            for job in jobs_list:
                values.append((
                    job.get('job_title', '')[:500],
                    job.get('company_name', '')[:200],
                    job.get('job_url', '')[:1000],
                    job.get('job_description', ''),
                    job.get('experience_required', '')[:100],
                    job.get('location', '')[:200],
                    job.get('posted_date'),
                    job.get('salary', '')[:200],
                    job.get('employment_type', '')[:100],
                    job.get('date_posted', '')[:100],
                    job.get('raw_text', '')
                ))
            
            execute_values(cursor, insert_query, values)
            saved_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return saved_count
            
        except Exception as e:
            logging.error(f"Error saving jobs: {e}")
            return 0
    
    def get_unsent_jobs(self, limit=50):
        """Get jobs that haven't been notified about yet"""
        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT job_title, company_name, job_url, location, experience_required, date_posted
                FROM jobs 
                WHERE notification_sent = FALSE 
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            
            jobs = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [
                {
                    'job_title': job[0],
                    'company_name': job[1],
                    'job_url': job[2],
                    'location': job[3],
                    'experience_required': job[4],
                    'date_posted': job[5]
                }
                for job in jobs
            ]
            
        except Exception as e:
            logging.error(f"Error getting unsent jobs: {e}")
            return []
    
    def mark_jobs_notified(self, job_urls):
        """Mark jobs as notified"""
        if not job_urls:
            return
        
        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE jobs 
                SET notification_sent = TRUE 
                WHERE job_url = ANY(%s)
            """, (job_urls,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error marking jobs as notified: {e}")

class NotificationManager:
    def __init__(self):
        self.email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'email_user': os.getenv('EMAIL_USER', ''),
            'email_password': os.getenv('EMAIL_PASSWORD', ''),
            'recipient_email': os.getenv('EMAIL_RECIPIENTS', '')
        }
    
    def send_email_notification(self, jobs):
        """Send email notification with CSV attachment containing all jobs"""
        if not jobs or not self.email_config['email_user']:
            return False
        
        try:
            # Create CSV file with all jobs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"new_jobs_{timestamp}.csv"
            
            # Write jobs to CSV
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow([
                    'Job Title', 'Company', 'Location', 'Experience Required',
                    'Date Posted', 'Apply URL', 'Job Description'
                ])
                
                # Data rows
                for job in jobs:
                    writer.writerow([
                        job.get('job_title', ''),
                        job.get('company_name', ''),
                        job.get('location', ''),
                        job.get('experience_required', ''),
                        job.get('date_posted', 'Recently'),
                        job.get('job_url', ''),
                        (job.get('raw_text', '') or '')[:500] + '...' if job.get('raw_text') and len(job.get('raw_text', '')) > 500 else job.get('raw_text', '')
                    ])
            
            # Create email content
            subject = f"🚀 {len(jobs)} New Entry-Level Tech Jobs Found! (CSV Attached)"
            
            # Count jobs by company for summary
            company_counts = {}
            for job in jobs:
                company = job['company_name']
                company_counts[company] = company_counts.get(company, 0) + 1
            
            # Create simple text email body
            body = f"""
🚀 NEW JOBS FOUND: {len(jobs)} Entry-Level Tech Positions!

📊 COMPANY BREAKDOWN:
"""
            for company, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True):
                body += f"• {company}: {count} jobs\n"
            
            body += f"""

📎 ATTACHED: Complete job list in CSV format
📂 FILE: {csv_filename}
---
This notification was sent by your automated job scraper.
Run 'python3 improved_hourly_scraper.py' to find more jobs.
"""
            
            # Create email message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.email_config['email_user']
            msg['To'] = self.email_config['recipient_email']
            
            # Add text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add CSV attachment
            with open(csv_filename, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {csv_filename}'
            )
            msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['email_user'], self.email_config['email_password'])
                server.send_message(msg)
            
            # Clean up CSV file
            import os
            os.remove(csv_filename)
            
            logging.info(f"Email notification sent for {len(jobs)} jobs with CSV attachment")
            return True
            
        except Exception as e:
            logging.error(f"Error sending email: {e}")
            return False

    def send_email_notification_no_jobs(self):
        """Send email notification to mention there are no new jobs"""
        if not self.email_config['email_user']:
            return False

        try:
            # Create email content
            subject = f"🚀 No New Entry-Level Tech Jobs Found"

            # Create simple text email body
            body = f"""
        🚀 No NEW Entry-Level Tech Positions JOBS FOUND in this execution!
        
        ---
        This notification was sent by your automated job scraper.
        Run 'python3 improved_hourly_scraper.py' to find more jobs.
        """

            # Create email message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.email_config['email_user']
            msg['To'] = self.email_config['recipient_email']

            # Add text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['email_user'], self.email_config['email_password'])
                server.send_message(msg)

            logging.info(f"No jobs found email notification sent.")
            return True

        except Exception as e:
            logging.error(f"Error sending email: {e}")
            return False

class DateParser:
    """Parse various date formats from job postings"""
    
    @staticmethod
    def parse_relative_date(date_text):
        """Parse relative dates like '2 days ago', 'yesterday', etc."""
        if not date_text:
            return None
        
        date_text = date_text.lower().strip()
        now = datetime.now()
        
        # Handle "today"
        if 'today' in date_text or 'just now' in date_text:
            return now
        
        # Handle "yesterday"
        if 'yesterday' in date_text:
            return now - timedelta(days=1)
        
        # Handle "X days ago"
        day_match = re.search(r'(\d+)\s*days?\s*ago', date_text)
        if day_match:
            days = int(day_match.group(1))
            return now - timedelta(days=days)
        
        # Handle "X hours ago"
        hour_match = re.search(r'(\d+)\s*hours?\s*ago', date_text)
        if hour_match:
            hours = int(hour_match.group(1))
            return now - timedelta(hours=hours)
        
        # Handle "X weeks ago"
        week_match = re.search(r'(\d+)\s*weeks?\s*ago', date_text)
        if week_match:
            weeks = int(week_match.group(1))
            return now - timedelta(weeks=weeks)
        
        # Handle "last week"
        if 'last week' in date_text:
            return now - timedelta(weeks=1)
        
        return None
    
    @staticmethod
    def is_recent_job(date_text, max_days=7):
        """Check if job was posted within max_days"""
        if not date_text:
            return True  # Assume recent if no date
        
        parsed_date = DateParser.parse_relative_date(date_text)
        if not parsed_date:
            return True  # Assume recent if can't parse
        
        days_old = (datetime.now() - parsed_date).days
        return days_old <= max_days

class ImprovedJobScraper:
    """Improved job scraper with better detection and time filtering"""
    
    def __init__(self, max_jobs_per_company=15, max_workers=8, timeout=8, max_days_old=7):
        self.max_jobs_per_company = max_jobs_per_company
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_days_old = max_days_old  # Only scrape jobs from last N days
        
        self.db = JobDatabase()
        self.notifier = NotificationManager()
        self.date_parser = DateParser()
        
        # Expanded tech keywords for better detection
        self.tech_keywords = [
            'engineer', 'developer', 'software', 'programmer', 'sde', 'swe',
            'analyst', 'scientist', 'architect', 'intern', 'associate', 'dev',
            'coder', 'qa', 'quality assurance', 'devops', 'full stack', 'frontend',
            'backend', 'data', 'machine learning', 'ai', 'cloud', 'security',
            'mobile', 'web', 'application', 'systems', 'technical', 'it'
        ]
        
        # More comprehensive entry-level keywords
        self.entry_level_keywords = [
            'entry level', 'entry-level', 'junior', 'jr', 'associate', 'new grad',
            'recent grad', 'graduate', 'intern', 'trainee', 'level 1', 'level i',
            'sde i', 'sde 1', 'engineer i', 'engineer 1', '0-2 years', '1-2 years', '2-3 years',
            'no experience', 'fresh', 'beginner', 'apprentice', 'assistant','1+ years', '2+ years', '3+ years'
        ]
        
        # Senior disqualifiers
        self.senior_keywords = [
            'senior', 'sr.', 'lead', 'principal', 'staff', 'manager', 'director',
            'head of', 'vp', 'vice president', 'chief', 'sde iii', 'sde 3',
            'sde iv', 'sde 4', 'level 3', 'level 4', 'level 5',
            '5+ years', '6+ years', '7+ years', '8+ years', '9+ years', '10+ years'
        ]
        
        # USA and remote keywords
        self.usa_keywords = [
            'usa', 'united states', 'us', 'remote', 'work from home', 'telecommute',
            'california', 'ca', 'new york', 'ny', 'texas', 'tx', 'washington', 'wa',
            'florida', 'fl', 'seattle', 'san francisco', 'chicago', 'boston',
            'austin', 'denver', 'atlanta', 'los angeles', 'silicon valley',
            'bay area', 'portland', 'philadelphia', 'phoenix', 'dallas', 'miami'
        ]
    
    def create_driver(self):
        """Create optimized Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(3)
        driver.set_page_load_timeout(self.timeout)
        
        return driver
    
    def scrape_with_http(self, company_name, url):
        """Fast HTTP-based scraping with improved job detection"""
        jobs = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Multiple strategies to find job elements
            job_elements = []
            
            # Strategy 1: Look for common job selectors
            job_selectors = [
                'div[class*="job"]', 'li[class*="job"]', 'article[class*="job"]',
                'div[class*="position"]', 'div[class*="opening"]', 'div[class*="role"]',
                'a[href*="/job"]', 'a[href*="/jobs/"]', 'a[href*="/career"]',
                '[data-job-id]', '[data-automation-id*="job"]', '.search-result',
                '.job-result', '.position', '.opportunity'
            ]
            
            for selector in job_selectors:
                elements = soup.select(selector)
                if elements:
                    job_elements = elements
                    logging.debug(f"Found {len(elements)} elements with selector: {selector}")
                    break
            
            # Strategy 2: Look for links with job-related keywords in href or text
            if not job_elements:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '').lower()
                    text = link.get_text(strip=True).lower()
                    
                    # Check if link looks like a job
                    if (any(keyword in href for keyword in ['/job', '/career', '/position', '/opening']) or
                        any(keyword in text for keyword in self.tech_keywords) and len(text) > 10):
                        job_elements.append(link)
            
            # Extract job data
            logging.info(f"Processing {len(job_elements)} potential job elements for {company_name}")
            
            for element in job_elements:
                try:
                    job_data = self.extract_job_data_http(element, company_name, url)
                    if job_data and self.is_valid_job(job_data):
                        jobs.append(job_data)
                        if len(jobs) >= self.max_jobs_per_company:
                            break
                except Exception as e:
                    logging.debug(f"Error extracting job data: {e}")
                    continue
            
            logging.info(f"Found {len(jobs)} valid jobs from {company_name} (HTTP)")
            return jobs
            
        except Exception as e:
            logging.error(f"HTTP scraping failed for {company_name}: {e}")
            return []
    
    def scrape_with_selenium(self, company_name, url):
        """Selenium-based scraping with improved detection"""
        jobs = []
        driver = None
        
        try:
            driver = self.create_driver()
            driver.get(url)
            time.sleep(3)
            
            # Scroll to load content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Multiple strategies to find job elements
            job_selectors = [
                'div[class*="job"]', 'li[class*="job"]', 'a[href*="/job"]',
                '[data-testid*="job"]', '[role="listitem"]', '.search-result',
                '.job-result', '.position', '.opportunity', 'article'
            ]
            
            job_elements = []
            for selector in job_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        job_elements = elements
                        logging.debug(f"Found {len(elements)} elements with selector: {selector}")
                        break
                except:
                    continue
            
            # Fallback: find all links and filter
            if not job_elements:
                all_links = driver.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    try:
                        href = link.get_attribute('href') or ''
                        text = link.text.strip()
                        if (any(keyword in href.lower() for keyword in ['/job', '/career']) or
                            any(keyword in text.lower() for keyword in self.tech_keywords)):
                            job_elements.append(link)
                    except:
                        continue
            
            logging.info(f"Processing {len(job_elements)} potential job elements for {company_name}")
            
            # Extract job data
            for element in job_elements:
                try:
                    job_data = self.extract_job_data_selenium(element, company_name, url)
                    if job_data and self.is_valid_job(job_data):
                        jobs.append(job_data)
                        if len(jobs) >= self.max_jobs_per_company:
                            break
                except Exception as e:
                    logging.debug(f"Error extracting job data: {e}")
                    continue
            
            logging.info(f"Found {len(jobs)} valid jobs from {company_name} (Selenium)")
            return jobs
            
        except Exception as e:
            logging.error(f"Selenium scraping failed for {company_name}: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def extract_job_data_http(self, element, company_name, base_url):
        """Extract job data from BeautifulSoup element"""
        try:
            raw_text = element.get_text(separator=' ', strip=True)
            
            # Extract title
            title = ""
            if element.name == 'a':
                title = element.get_text(strip=True)
            else:
                # Look for title in various elements
                title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Use first line that looks like a title
                    lines = raw_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if len(line) > 10 and any(keyword in line.lower() for keyword in self.tech_keywords):
                            title = line
                            break
            
            # Extract URL
            url = ""
            if element.name == 'a':
                url = element.get('href')
            else:
                link = element.find('a')
                if link:
                    url = link.get('href')
            
            if url and not url.startswith('http'):
                url = urljoin(base_url, url)
            
            # Extract location
            location = self.extract_location(raw_text)
            
            # Extract date posted
            date_posted = self.extract_date_posted(raw_text)
            
            return {
                'company_name': company_name,
                'job_title': title,
                'job_url': url,
                'location': location,
                'job_description': raw_text[:500],
                'experience_required': self.analyze_experience_level(title, raw_text),
                'posted_date': self.date_parser.parse_relative_date(date_posted),
                'date_posted': date_posted,
                'salary': self.extract_salary(raw_text),
                'employment_type': self.extract_employment_type(raw_text),
                'raw_text': raw_text
            }
            
        except Exception as e:
            logging.debug(f"Error in extract_job_data_http: {e}")
            return None
    
    def extract_job_data_selenium(self, element, company_name, base_url):
        """Extract job data from Selenium element"""
        try:
            raw_text = element.text.strip()
            
            # Extract title
            title = ""
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, 'h1, h2, h3, h4, h5')
                title = title_elem.text.strip()
            except:
                # Use first line that looks like a title
                lines = raw_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 10 and any(keyword in line.lower() for keyword in self.tech_keywords):
                        title = line
                        break
            
            # Extract URL
            url = ""
            if element.tag_name == 'a':
                url = element.get_attribute('href')
            else:
                try:
                    link = element.find_element(By.TAG_NAME, 'a')
                    url = link.get_attribute('href')
                except:
                    pass
            
            if url and not url.startswith('http'):
                url = urljoin(base_url, url)
            
            # Extract location
            location = self.extract_location(raw_text)
            
            # Extract date posted
            date_posted = self.extract_date_posted(raw_text)
            
            return {
                'company_name': company_name,
                'job_title': title,
                'job_url': url,
                'location': location,
                'job_description': raw_text[:500],
                'experience_required': self.analyze_experience_level(title, raw_text),
                'posted_date': self.date_parser.parse_relative_date(date_posted),
                'date_posted': date_posted,
                'salary': self.extract_salary(raw_text),
                'employment_type': self.extract_employment_type(raw_text),
                'raw_text': raw_text
            }
            
        except Exception as e:
            logging.debug(f"Error in extract_job_data_selenium: {e}")
            return None
    
    def extract_location(self, text):
        """Extract location from job text"""
        text_lower = text.lower()
        
        # Look for USA keywords
        for keyword in self.usa_keywords:
            if keyword in text_lower:
                # Try to extract the surrounding context
                lines = text.split('\n')
                for line in lines:
                    if keyword in line.lower():
                        return line.strip()[:100]
        
        return ""
    
    def extract_date_posted(self, text):
        """Extract date posted from job text"""
        # Common date patterns
        date_patterns = [
            r'(\d+\s*days?\s*ago)',
            r'(\d+\s*hours?\s*ago)',
            r'(\d+\s*weeks?\s*ago)',
            r'(yesterday)',
            r'(today)',
            r'(just now)',
            r'(last week)',
            r'(posted\s+\d+\s*days?\s*ago)',
            r'(posted\s+yesterday)',
            r'(posted\s+today)'
        ]
        
        text_lower = text.lower()
        for pattern in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1)
        
        return ""
    
    def extract_salary(self, text):
        """Extract salary information from job text"""
        salary_patterns = [
            r'\$[\d,]+\s*-\s*\$[\d,]+',
            r'\$[\d,]+k?\s*-\s*\$?[\d,]+k?',
            r'salary:\s*\$[\d,]+',
            r'[\d,]+k?\s*-\s*[\d,]+k?\s*(?:per year|annually)'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""
    
    def extract_employment_type(self, text):
        """Extract employment type from job text"""
        text_lower = text.lower()
        
        employment_types = {
            'full-time': 'Full-time',
            'full time': 'Full-time', 
            'part-time': 'Part-time',
            'part time': 'Part-time',
            'contract': 'Contract',
            'contractor': 'Contract',
            'internship': 'Internship',
            'intern': 'Internship',
            'temporary': 'Temporary',
            'remote': 'Remote'
        }
        
        for key, value in employment_types.items():
            if key in text_lower:
                return value
        
        return ""
    
    def analyze_experience_level(self, title, description):
        """Improved experience level analysis"""
        title_lower = title.lower()
        desc_lower = description.lower()
        full_text = f"{title_lower} {desc_lower}"
        
        # Check for senior indicators in title (strict)
        if any(keyword in title_lower for keyword in self.senior_keywords):
            return "Senior Level"
        
        # Check for explicit entry level indicators
        if any(keyword in full_text for keyword in self.entry_level_keywords):
            return "Entry Level"
        
        # Check for year requirements
        year_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)',
            r'minimum\s*(\d+)\s*years?',
            r'(\d+)\s*to\s*(\d+)\s*years?',
            r'(\d+)-(\d+)\s*years?'
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, full_text)
            for match in matches:
                if isinstance(match, tuple):
                    years = [int(x) for x in match if x.isdigit()]
                    min_years = min(years) if years else 0
                else:
                    min_years = int(match) if match.isdigit() else 0
                
                if min_years <= 2:
                    return "Entry Level"
                elif min_years > 3:
                    return "Senior Level"
        
        # Default to entry level for ambiguous cases
        return "Entry Level"
    
    def is_valid_job(self, job_data):
        """Improved job validation with more lenient but smart filtering"""
        title = job_data.get('job_title', '').lower()
        description = job_data.get('job_description', '').lower()
        location = job_data.get('location', '').lower()
        experience = job_data.get('experience_required', '').lower()
        date_posted = job_data.get('date_posted', '')
        
        # Must have reasonable title and URL
        if not job_data.get('job_title') or len(job_data.get('job_title', '')) < 5:
            return False
        
        if not job_data.get('job_url'):
            return False
        
        # Must be tech-related (more lenient)
        if not any(keyword in title for keyword in self.tech_keywords):
            # Check description too
            if not any(keyword in description for keyword in self.tech_keywords):
                return False
        
        # Skip obvious senior roles
        if 'senior' in experience.lower():
            return False
        
        # Check if job is recent (within max_days_old)
        if not self.date_parser.is_recent_job(date_posted, self.max_days_old):
            logging.debug(f"Skipping old job: {title} (posted: {date_posted})")
            return False
        
        # Must be in USA or remote (more lenient)
        full_text = f"{title} {description} {location}"
        if not any(keyword in full_text for keyword in self.usa_keywords):
            # Check if it mentions any international locations (exclude those)
            international_keywords = [
                'london', 'uk', 'canada', 'toronto', 'vancouver', 'india', 'bangalore',
                'hyderabad', 'mumbai', 'delhi', 'china', 'beijing', 'shanghai',
                'europe', 'germany', 'france', 'australia', 'singapore', 'japan'
            ]
            
            if any(keyword in full_text for keyword in international_keywords):
                return False
            
            # If no location specified, assume it might be USA (more lenient)
            if not location:
                pass  # Allow jobs with no clear location
            else:
                return False
        
        return True
    
    def get_scraping_strategy(self, company_name):
        """Determine best scraping strategy for company"""
        company_lower = company_name.lower()
        
        # Companies that work better with Selenium
        selenium_companies = [
            'meta', 'facebook', 'google', 'alphabet', 'netflix', 'airbnb',
            'uber', 'lyft', 'stripe', 'figma', 'databricks'
        ]
        
        for selenium_company in selenium_companies:
            if selenium_company in company_lower:
                return 'selenium'
        
        return 'http'  # Default to faster HTTP
    
    def scrape_company(self, company_data):
        """Scrape a single company using optimal strategy"""
        company_name = company_data['company']
        url = company_data['website']
        
        strategy = self.get_scraping_strategy(company_name)
        
        try:
            logging.info(f"Scraping {company_name} using {strategy} strategy")
            
            if strategy == 'selenium':
                jobs = self.scrape_with_selenium(company_name, url)
            else:
                jobs = self.scrape_with_http(company_name, url)
            
            return {
                'company': company_name,
                'jobs': jobs,
                'success': True,
                'strategy': strategy
            }
            
        except Exception as e:
            logging.error(f"Error scraping {company_name}: {e}")
            return {
                'company': company_name,
                'jobs': [],
                'success': False,
                'error': str(e),
                'strategy': strategy
            }
    
    def run_scraping_cycle(self, companies_file='companies_list.csv'):
        """Run one complete scraping cycle"""
        start_time = time.time()
        
        try:
            # Read companies
            df = pd.read_csv(companies_file, delimiter='|')
            companies = df.to_dict('records')
            
            logging.info(f"Starting improved scraping cycle for {len(companies)} companies")
            logging.info(f"Configuration: max_jobs={self.max_jobs_per_company}, max_days_old={self.max_days_old}")
            
            all_jobs = []
            
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_company = {
                    executor.submit(self.scrape_company, company): company['company']
                    for company in companies
                }
                
                for future in as_completed(future_to_company):
                    company_name = future_to_company[future]
                    try:
                        result = future.result()
                        if result['success']:
                            all_jobs.extend(result['jobs'])
                            logging.info(f"✓ {company_name} ({result['strategy']}): {len(result['jobs'])} jobs")
                        else:
                            logging.warning(f"✗ {company_name}: Failed")
                    except Exception as e:
                        logging.error(f"✗ {company_name}: {e}")
            
            # Save jobs to database
            saved_count = self.db.bulk_save_jobs(all_jobs)
            
            # Send notifications for new jobs
            if saved_count > 0:
                unsent_jobs = self.db.get_unsent_jobs()
                if unsent_jobs:
                    # Send email notification
                    if self.notifier.send_email_notification(unsent_jobs):
                        # Mark jobs as notified
                        job_urls = [job['job_url'] for job in unsent_jobs]
                        self.db.mark_jobs_notified(job_urls)
            else:
                self.notifier.send_email_notification_no_jobs()
            
            elapsed_time = time.time() - start_time
            
            logging.info(f"""
            ========================================
            IMPROVED SCRAPING CYCLE COMPLETED
            ========================================
            Companies processed: {len(companies)}
            Total jobs found: {len(all_jobs)}
            New jobs saved: {saved_count}
            Time elapsed: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)
            Jobs per company (avg): {len(all_jobs)/len(companies):.1f}
            Recent jobs only: Last {self.max_days_old} days
            Notifications sent: {'Yes' if saved_count > 0 else 'No'}
            """)
            
            return saved_count
            
        except Exception as e:
            logging.error(f"Error in scraping cycle: {e}")
            return 0

def run_hourly_scheduler():
    """Run the improved scraper every hour"""
    scraper = ImprovedJobScraper(
        max_jobs_per_company=20,  # Increased to get more jobs
        max_workers=8,
        timeout=8,
        max_days_old=7  # Only jobs from last 7 days
    )
    
    def scheduled_job():
        logging.info("="*60)
        logging.info(f"STARTING HOURLY IMPROVED JOB SCRAPING - {datetime.now()}")
        logging.info("="*60)
        
        new_jobs = scraper.run_scraping_cycle('companies_list.csv')
        
        logging.info(f"Hourly scraping completed: {new_jobs} new jobs found")
        logging.info("="*60)
    
    # Schedule every hour
    schedule.every().hour.do(scheduled_job)
    
    # Run once immediately
    scheduled_job()
    
    # Keep running
    logging.info("🚀 Improved hourly job scraper started!")
    logging.info("⏰ Configured to find jobs from last 7 days only")
    logging.info("Press Ctrl+C to stop.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Improved scraper stopped by user")

def main():
    """Test the improved scraper"""
    print("""
    🚀 IMPROVED HOURLY JOB SCRAPER 🚀
    
    Improvements:
    ✅ Better job detection (more lenient but smart filtering)
    ✅ Time-based filtering (only jobs from last 7 days)
    ✅ Enhanced experience level analysis
    ✅ Improved location detection
    ✅ Date parsing for job posting dates
    ✅ More comprehensive tech keyword matching
    
    Starting improved scraper...
    """)
    
    run_hourly_scheduler()

if __name__ == "__main__":
    main() 