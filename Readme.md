# Gmail LinkedIn Application Tracker

This Python script connects to your Gmail account via the Gmail API, finds job application confirmation and rejection emails from LinkedIn, and generates:

- `applied_companies.txt` → List of companies you have applied to (with dates, sorted by date)
- `rejected_applications.txt` → List of applications that were rejected (with position, company, and date)
- `distinct_companies.txt` → Cleaned, deduplicated list of all companies (with original names)
- `distinct_companies_simple.txt` → Simple list of unique company names (cleaned, lowercase)

It helps you keep track of your job applications and avoid reapplying to the same companies.

---

## ⚙️ Setup Instructions

### 1. Enable Gmail API & Create OAuth 2.0 Credentials

You need to set up Gmail API access so the script can read your emails.

1. Go to the **Google Cloud Console**:  
   [https://console.cloud.google.com/](https://console.cloud.google.com/)

2. **Create a new project** (or select an existing one).

3. **Enable the Gmail API**:

   - Go to [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
   - Click **Enable**.

4. **Create OAuth 2.0 credentials**:

   - Go to **APIs & Services → Credentials**:  
     [https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
   - Click **Create Credentials → OAuth client ID**.
   - If prompted, configure the **OAuth consent screen**:
     - Select **External**
     - Fill in the required fields (App name, email, etc.)
     - Add yourself as a **test user**
     - Save and continue
   - Choose **Application type** → **Desktop app**
   - Name it (e.g., `Gmail LinkedIn Tracker`)
   - Click **Create**
   - **Download** the `credentials.json` file.

5. Place `credentials.json` in the same directory as this script.

---

### 2. Install Python Dependencies

Make sure you have Python 3 installed.  
Then install required libraries:

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 3. Run the Script

```bash
python script.py
```

- On first run, a browser window will open asking you to log in with your Google account and grant read-only access to Gmail.

- After authorizing, the script will store a token.json so you don’t need to log in again.

## How It Works

1. The script queries Gmail for:

   - "application was sent to" (from LinkedIn) → Applied companies

   - "Your application to" → Rejected applications

2. It extracts company names from the email snippets and subjects.

3. Names are cleaned using Unicode normalization and suffix removal (e.g., "Pte Ltd", "Inc").

4. Deduplication uses:

   - String cleaning

   - Substring fuzzy matching

5. Results are sorted by date and written to text files.

## Notes & Limitations

- The script only reads emails in your Gmail account that match the LinkedIn application/rejection format.

- If you applied via other platforms, those won’t be detected.

- If you want to run it again later, just execute the script — it will reuse your saved token.
