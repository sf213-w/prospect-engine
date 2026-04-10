import httpx
from bs4 import BeautifulSoup
import llm
import json
import os
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

# 1. Keep your Schema
class BreachInfo(BaseModel):
    victim_company: str
    vendor_involved: Optional[str] = "N/A"
    date_reported: str
    summary: str
    breach_type: str
    is_actual_breach: bool

class BreachList(BaseModel):
    breaches: List[BreachInfo]

def scrape_and_extract(url: str, model):
    print(f"\n--- Fetching: {url} ---")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = httpx.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Clean noise
        main_content = soup.find('main') or soup.find('body')
        for tag in main_content(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        content = main_content.get_text(separator=" ", strip=True)[:10000]
        
        system_prompt = (
            "You are a Cyber Intelligence bot. Extract specific data breach incidents. "
            "Ignore general software updates or vulnerabilities unless a specific company was victimized. "
            "Return an empty list if no breaches are found."
        )

        # Process with the model passed from the loop
        response = model.prompt(
            f"Analyze this news for data breaches:\n\n{content}",
            system=system_prompt,
            schema=BreachList
        )
        return response.json()

    except Exception as e:
        print(f"Error scanning {url}: {e}")
        return None

if __name__ == "__main__":
    target_websites = [
        "https://www.bleepingcomputer.com/",
        "https://thehackernews.com/",
        "https://www.securityweek.com/",
        "https://krebsonsecurity.com/"
    ]

    llama = llm.get_model("llama3.2")
    all_found_breaches = []

    for site in target_websites:
        data = scrape_and_extract(site, llama)
        
        if data and data.get("breaches"):
            print(f"Success! Found {len(data['breaches'])} potential items on {site}")
            for b in data["breaches"]:
                if b.get("is_actual_breach"):
                    # Map LLM output to Dashboard-compatible format
                    dashboard_item = {
                        "published": b.get("date_reported", datetime.now().isoformat()),
                        "title": f"Breach: {b.get('victim_company')}",
                        "source": site,
                        "summary": b.get("summary"),
                        "url": site # Using site as placeholder; update scrape_and_extract to return specific article URLs if possible
                    }
                    all_found_breaches.append(dashboard_item)
        else:
            print(f"No confirmed breaches found on {site}.")

    # 3. Final Summary and File Export
    print("\n" + "="*50)
    print(f"SCAN COMPLETE: Found {len(all_found_breaches)} verified incidents.")
    print("="*50)
    
    if all_found_breaches:
        # Prepare the dashboard JSON structure
        output_data = {
            "generated": datetime.now().isoformat(),
            "lookback_days": 7,
            "articles": all_found_breaches
        }

        # Create breach_reports directory if it doesn't exist
        os.makedirs("breach_reports", exist_ok=True)
        
        # Save file with required timestamp naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"breach_reports/breaches_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(output_data, f, indent=2)
            
        print(f"SUCCESS: Report saved for dashboard at {filename}")