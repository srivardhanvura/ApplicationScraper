# 📧 EMAIL SETUP GUIDE

## 🎯 **Quick Answer**: 
**No, you don't need to create a new email!** You can use your existing Gmail account.

---

## 📋 **STEP-BY-STEP SETUP**

### **Option 1: Use Your Existing Gmail (Recommended)**

#### **Step 1: Enable App Passwords**
1. Go to your **Google Account settings**: https://myaccount.google.com/
2. Click **Security** in the left sidebar
3. Under "Signing in to Google", click **2-Step Verification** 
4. Scroll down and click **App passwords**
5. Select **Mail** and **Other (custom name)**
6. Type "Job Scraper" as the name
7. Click **Generate**
8. **Copy the 16-character password** (you'll need this!)

#### **Step 2: Configure Your .env File**
```bash
# Copy the template
cp env_template.txt .env

# Edit the .env file with your credentials
```

**Edit `.env` file:**
```
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_actual_email@gmail.com
EMAIL_PASSWORD=your_16_character_app_password
RECIPIENT_EMAIL=your_actual_email@gmail.com
```

**Example:**
```
EMAIL_USER=john.doe@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop
RECIPIENT_EMAIL=john.doe@gmail.com
```

---

### **Option 2: Create Dedicated Gmail Account (More Secure)**

If you prefer a separate account:

1. **Create new Gmail**: Go to gmail.com → Create Account
2. **Choose a name** like: `jobscraper.yourname@gmail.com`
3. **Enable 2FA and App Password** (same steps as Option 1)
4. **Use the new email** in your `.env` file

---

### **Option 3: Use Other Email Providers**

#### **Yahoo Mail:**
```
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
EMAIL_USER=your_email@yahoo.com
EMAIL_PASSWORD=your_app_password
```

#### **Outlook/Hotmail:**
```
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
EMAIL_USER=your_email@outlook.com
EMAIL_PASSWORD=your_password
```

---

## ⚠️ **IMPORTANT SECURITY NOTES**

1. **Never use your regular password** - Always use App Passwords for Gmail
2. **Keep .env file private** - It's already in .gitignore
3. **The .env file should look like this:**
   ```
   # Database Configuration  
   DB_HOST=localhost
   DB_NAME=job_scraper
   DB_USER=postgres
   DB_PASSWORD=your_postgres_password
   
   # Email Configuration
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   RECIPIENT_EMAIL=your_email@gmail.com
   ```

---

## 🧪 **TEST YOUR EMAIL SETUP**

### **Quick Configuration Check:**
```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('EMAIL_USER:', os.getenv('EMAIL_USER'))
print('EMAIL_PASSWORD:', '***' if os.getenv('EMAIL_PASSWORD') else 'NOT SET')
print('RECIPIENT_EMAIL:', os.getenv('RECIPIENT_EMAIL'))
"
```

### **Full Email Test:**
**Run the scraper to test the complete email + CSV flow:**
```bash
python3 improved_hourly_scraper.py
```
**This will:**
- ✅ Find new jobs and send email with CSV attachment
- ✅ Show you exactly what the production emails look like
- ✅ Verify the complete notification system

---

## 📨 **WHAT YOU'LL RECEIVE**

When jobs are found, you'll get emails with **CSV attachments**:

**Subject:** 🚀 12 New Entry-Level Tech Jobs Found! (CSV Attached)

**Email Content:**
- Summary of jobs by company
- Instructions for using the CSV file
- Quick action items

**CSV Attachment Contains:**
- ✅ **ALL job details** in spreadsheet format
- ✅ **Direct apply URLs** (clickable in Excel/Sheets)
- ✅ **Job descriptions** (truncated to 500 chars)
- ✅ **Sortable columns**: Company, Location, Experience, Date
- ✅ **Easy to filter** and organize

**Example Email:**
```
🚀 NEW JOBS FOUND: 12 Entry-Level Tech Positions!

📊 COMPANY BREAKDOWN:
• Google: 3 jobs
• Microsoft: 2 jobs
• Apple: 2 jobs
• Stripe: 5 jobs

📎 ATTACHED: Complete job list in CSV format
📂 FILE: new_jobs_20250620_142154.csv

💡 QUICK ACTIONS:
• Open CSV in Excel/Google Sheets for easy viewing
• Sort by company, location, or date posted
• Click URLs to apply directly
```

---

## 🔧 **TROUBLESHOOTING**

### **"Authentication failed" Error:**
- ✅ Make sure you're using an **App Password**, not your regular password
- ✅ Check that 2-Factor Authentication is enabled
- ✅ Verify the email address is correct

### **"Connection timeout" Error:**
- ✅ Check your internet connection
- ✅ Try using port 465 instead of 587
- ✅ Make sure your firewall isn't blocking SMTP

### **No emails received:**
- ✅ Check spam/junk folder
- ✅ Verify RECIPIENT_EMAIL is correct
- ✅ Run the test command above

---

## 🚀 **NEXT STEPS**

1. **Setup email** (follow steps above)
2. **Test the scraper**: `python3 test_improved_scraper.py`
3. **Run production**: `python3 improved_hourly_scraper.py`
4. **Check your email** for job notifications! 📬

---

## 💡 **PRO TIPS**

- **Gmail is most reliable** for this setup
- **Use a dedicated email** if you want to keep work separate
- **The scraper only sends emails when NEW jobs are found**
- **You can change the recipient** to send notifications to a different email
- **Email notifications are automatic** - no manual intervention needed!

**Questions? The email will be sent to: `svvura@ncsu.edu` by default, but you can change this in the .env file.** 