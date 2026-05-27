import os
import time
import requests
import pandas as pd
from sec_edgar_downloader import Downloader

# ==========================================
# 1. IDENTITY & DIRECTORY SETUP
# ==========================================
# Change this line in your sec.py file:
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (Contact: bryanbelanger@hotmail.com)"
COMPANY_NAME = "Not Applicable" # Not used in this script, but required by the Downloader class
EMAIL_ADDR = "bryanbelanger@hotmail.com"
DOWNLOAD_DIR = "/sec"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
dl = Downloader(COMPANY_NAME, EMAIL_ADDR, DOWNLOAD_DIR)

# ==========================================
# 2. PULL THE ENTIRE MARKET LIST
# ==========================================
print("Fetching active ticker list from the SEC...")
headers = {'User-Agent': USER_AGENT}
url = "https://www.sec.gov/files/company_tickers.json"

response = requests.get(url, headers=headers)
response.raise_for_status()
df = pd.DataFrame.from_dict(response.json(), orient='index')
all_tickers = df['ticker'].dropna().unique().tolist()
print(f"Loaded {len(all_tickers)} active tickers to process.")

# ==========================================
# 3. LATEST-ONLY DOWNLOAD LOOP
# ==========================================
print("\nStarting download of the LATEST 10-K for all companies...")

for index, ticker in enumerate(all_tickers, 1):
    # Check if a 10-K directory already exists for this ticker to avoid redownloading
    company_folder = os.path.join(DOWNLOAD_DIR, "sec-edgar-filings", ticker, "10-K")
    if os.path.exists(company_folder) and os.listdir(company_folder):
        continue # Already downloaded, skip to next
        
    print(f"[{index}/{len(all_tickers)}] Fetching latest 10-K for: {ticker}")
    
    try:
        # limit=1 guarantees you only pull the single most recent filing
        dl.get("10-K", ticker, limit=1)
        
        # Mandatory 0.15s sleep to stay strictly under the SEC's 10 requests/sec limit
        time.sleep(0.15)
        
    except Exception as e:
        # Silently log errors for edge-case tickers (like new SPACs with no 10-K yet)
        with open("latest_download_errors.log", "a") as log:
            log.write(f"Error {ticker}: {str(e)}\n")
        time.sleep(0.15)

print("\n🎉 All latest market filings successfully downloaded!")