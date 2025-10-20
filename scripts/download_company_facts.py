"""
Download and prepare the SEC company facts data.
"""
import os
import requests
import pandas as pd
import json

def download_company_facts():
    # SEC company tickers endpoint
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        "User-Agent": os.getenv("SEC_USER_AGENT", "EdgarTest/1.0")
    }
    
    print("Downloading company facts from SEC...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Convert the JSON data to a DataFrame
    data = response.json()
    companies = []
    for _, company in data.items():
        companies.append({
            'ticker': company['ticker'],
            'cik_str': str(company['cik_str']).zfill(10),
            'title': company['title']
        })
    
    df = pd.DataFrame(companies)
    
    # Save to CSV
    output_path = "Data/Primary/kaggle_info/companyfacts.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} companies to {output_path}")
    print("\nFirst few companies:")
    print(df.head())

if __name__ == "__main__":
    download_company_facts()