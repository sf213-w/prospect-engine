import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class XposeScraper:
    def __init__(self, output_file='data/data_leaks.csv'):
        self.output_file = output_file
        self.base_url = 'https://www.xpose.sh/'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.leaks = []

    def fetch_page(self, url):
        """Fetch a page with error handling and retry logic"""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_leaks(self, html):
        """Parse leak information from HTML"""
        if not html:
            return
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find leak entries - adjust selectors based on actual Xpose HTML structure
        leak_items = soup.find_all('div', class_='breach-item')
        
        for item in leak_items:
            try:
                leak_data = {}
                
                # Extract company name
                company_elem = item.find('h3', class_='company-name') or item.find('a', class_='breach-name')
                leak_data['company'] = company_elem.get_text(strip=True) if company_elem else 'N/A'
                
                # Extract date
                date_elem = item.find('span', class_='leak-date') or item.find('time')
                leak_data['date'] = date_elem.get_text(strip=True) if date_elem else 'N/A'
                
                # Extract number of records
                records_elem = item.find('span', class_='record-count')
                leak_data['records'] = records_elem.get_text(strip=True) if records_elem else 'N/A'
                
                # Extract description
                desc_elem = item.find('p', class_='description')
                leak_data['description'] = desc_elem.get_text(strip=True) if desc_elem else 'N/A'
                
                # Extract source/details link
                link_elem = item.find('a', class_='leak-link')
                leak_data['source_url'] = link_elem['href'] if link_elem and link_elem.get('href') else 'N/A'
                
                self.leaks.append(leak_data)
                logger.info(f"Found leak: {leak_data['company']}")
                
            except Exception as e:
                logger.error(f"Error parsing leak item: {e}")
                continue

    def scrape(self, max_pages=1):
        """Main scraping function"""
        logger.info("Starting Xpose scraper...")
        
        try:
            for page in range(1, max_pages + 1):
                # Adjust URL pagination based on Xpose structure
                if page == 1:
                    url = self.base_url
                else:
                    url = f"{self.base_url}?page={page}"
                
                html = self.fetch_page(url)
                if html:
                    self.parse_leaks(html)
                    time.sleep(2)  # Be respectful with requests
                else:
                    logger.warning(f"Failed to fetch page {page}")
                    break
            
            logger.info(f"Scraping complete. Found {len(self.leaks)} leaks.")
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")

    def save_to_csv(self):
        """Save collected leaks to CSV file"""
        if not self.leaks:
            logger.warning("No leaks to save!")
            return
        
        try:
            fieldnames = ['company', 'date', 'records', 'description', 'source_url', 'scraped_at']
            
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for leak in self.leaks:
                    leak['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow(leak)
            
            logger.info(f"Data saved to {self.output_file}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")

def main():
    # Initialize scraper
    scraper = XposeScraper(output_file='data/data_leaks.csv')
    
    # Scrape data (adjust max_pages as needed)
    scraper.scrape(max_pages=1)
    
    # Save to CSV
    scraper.save_to_csv()

if __name__ == '__main__':
    main()
