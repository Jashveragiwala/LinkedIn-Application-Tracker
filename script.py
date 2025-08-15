from __future__ import print_function
import os.path
import re
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import unicodedata

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def clean_company_name(name):
    """Clean and normalize company names for deduplication"""
    if not name:
        return ""
    
    # Normalize to NFC form to make Unicode characters consistent
    name = unicodedata.normalize("NFC", name)
    
    # Remove invisible Unicode characters and zero-width spaces
    name = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\u00ad]', '', name)
    
    # Remove any remaining invisible characters (like the ͏ characters in your sample)
    name = re.sub(r'[\u034f\u2800\u3164\uffa0\u115f\u1160\u180e\u200c\u200d]', '', name)
    
    # Remove common suffixes and prefixes that might cause duplicates
    suffixes_to_remove = [
        r'\s+pte\.?\s*ltd\.?$',
        r'\s+ltd\.?$',
        r'\s+inc\.?$',
        r'\s+llc\.?$',
        r'\s+corp\.?$',
        r'\s+corporation\.?$',
        r'\s+company\.?$',
        r'\s+co\.?$',
        r'\s+pvt\.?\s*ltd\.?$',
        r'\s+private\s+limited$',
        r'\s+limited$',
        r'\s+singapore\s*$',
        r'\s+sg\s*$'
    ]
    
    for suffix in suffixes_to_remove:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)
    
    # Collapse multiple spaces and normalize whitespace
    name = re.sub(r'\s+', ' ', name)
    
    # Strip leading/trailing spaces and convert to lowercase
    name = name.strip().lower()
    
    # Handle some specific cases that might still cause duplicates
    name = re.sub(r'^the\s+', '', name)  # Remove "the" at the beginning
    
    return name

def fuzzy_match_companies(companies_set):
    """Further deduplicate companies using fuzzy matching"""
    companies_list = list(companies_set)
    to_remove = set()
    
    for i, company1 in enumerate(companies_list):
        if company1 in to_remove:
            continue
            
        for j, company2 in enumerate(companies_list[i+1:], i+1):
            if company2 in to_remove:
                continue
            
            # Check if one is a substring of another (after cleaning)
            if company1 in company2 or company2 in company1:
                # Keep the shorter name (usually more canonical)
                if len(company1) <= len(company2):
                    to_remove.add(company2)
                else:
                    to_remove.add(company1)
                    break
    
    return companies_set - to_remove

def get_message_date(headers):
    """Extract and format the date from message headers."""
    for header in headers:
        if header['name'] == 'Date':
            try:
                return datetime.strptime(header['value'][:25], "%a, %d %b %Y %H:%M:%S")
            except Exception:
                return header['value']  # fallback raw date
    return "Unknown Date"

def fetch_all_messages(service, query):
    """Fetch all Gmail messages matching the query (with pagination)."""
    all_messages = []
    page_token = None

    while True:
        results = service.users().messages().list(
            userId='me', q=query, maxResults=200, pageToken=page_token
        ).execute()

        msgs = results.get('messages', [])
        all_messages.extend(msgs)

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return all_messages

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    # To collect distinct companies
    all_companies_set = set()
    # Keep original names for reference
    original_to_cleaned = {}

    # ------------------- 1. Applied Companies -------------------
    applied_query = 'from:linkedin.com "application was sent to"'
    applied_msgs = fetch_all_messages(service, applied_query)
    applied_list = []

    for msg in applied_msgs:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = msg_data['snippet']
        headers = msg_data['payload']['headers']
        date_sent = get_message_date(headers)

        match = re.search(r'sent to (.+)', snippet)
        if match and isinstance(date_sent, datetime):
            company = match.group(1).strip()
            applied_list.append((date_sent, company))
            
            cleaned_company = clean_company_name(company)
            if cleaned_company:  # Only add non-empty cleaned names
                all_companies_set.add(cleaned_company)
                # Keep track of original name for the cleaned version
                if cleaned_company not in original_to_cleaned:
                    original_to_cleaned[cleaned_company] = company

    applied_list.sort(key=lambda x: x[0], reverse=True)

    with open('applied_companies.txt', 'w', encoding='utf-8') as f:
        for date_sent, company in applied_list:
            f.write(f"{date_sent.strftime('%Y-%m-%d')} | {company}\n")

    # ------------------- 2. Rejected Applications -------------------
    rejected_query = 'subject:"Your application to"'
    rejected_msgs = fetch_all_messages(service, rejected_query)
    rejected_list = []

    for msg in rejected_msgs:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data['payload']['headers']
        date_sent = get_message_date(headers)

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
        match = re.search(r'Your application to (.+) at (.+)', subject)
        if match and isinstance(date_sent, datetime):
            position = match.group(1).strip()
            company = match.group(2).strip()
            rejected_list.append((date_sent, f"{position} @ {company}"))
            
            cleaned_company = clean_company_name(company)
            if cleaned_company:  # Only add non-empty cleaned names
                all_companies_set.add(cleaned_company)
                # Keep track of original name for the cleaned version
                if cleaned_company not in original_to_cleaned:
                    original_to_cleaned[cleaned_company] = company

    rejected_list.sort(key=lambda x: x[0], reverse=True)

    with open('rejected_applications.txt', 'w', encoding='utf-8') as f:
        for date_sent, details in rejected_list:
            f.write(f"{date_sent.strftime('%Y-%m-%d')} | {details}\n")

    # ------------------- 3. Distinct Companies with Fuzzy Matching -------------------
    # Apply fuzzy matching to further reduce duplicates
    all_companies_set = fuzzy_match_companies(all_companies_set)
    
    # Sort companies and write to file with original names
    distinct_companies = sorted(all_companies_set)
    
    with open('distinct_companies.txt', 'w', encoding='utf-8') as f:
        f.write("# Distinct Companies (cleaned names with original references)\n")
        f.write("# Format: cleaned_name | original_name\n\n")
        for company in distinct_companies:
            original_name = original_to_cleaned.get(company, company)
            f.write(f"{company} | {original_name}\n")
    
    # Also create a simple list for easy reference
    with open('distinct_companies_simple.txt', 'w', encoding='utf-8') as f:
        for company in distinct_companies:
            f.write(company + '\n')

    print(f"Saved {len(applied_list)} applied companies to applied_companies.txt")
    print(f"Saved {len(rejected_list)} rejected applications to rejected_applications.txt")
    print(f"Saved {len(distinct_companies)} unique companies to distinct_companies.txt")
    print(f"Also created distinct_companies_simple.txt with just the cleaned names")

if __name__ == '__main__':
    main()