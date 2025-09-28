import requests
import re
from bs4 import BeautifulSoup

# Replace with your API key and CSE ID
API_KEY = 'AIzaSyDSNb9Ak99yF64K2sc5LAjdSZJ0rLLFl8Q'  # From Google Cloud Credentials
CSE_ID = 'e47b6bcbeb6e64c9a'    # From cse.google.com

def lookup_organization(organization_name):
    """Search Google Custom Search for organization details."""
    query = f"{organization_name} contact details and timings"
    
    try:
        search_url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={CSE_ID}&q={query.replace(' ', '+')}&num=5"
        response = requests.get(search_url)
        response.raise_for_status()
        results = response.json()
        
        details = {
            'phone': None,
            'address': None,
            'hours': None,
            'website': None
        }
        
        # Extract from snippets and links
        for item in results.get('items', []):
            snippet = item.get('snippet', '')
            title = item.get('title', '')
            
            # Phone (regex for various formats like (800) 642-7676 or 480-858-1660)
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\d{10}', snippet)
            if phone_match and not details['phone']:
                details['phone'] = phone_match.group().strip()
            
            # Address (loosen regex to catch partial addresses)
            address_match = re.search(r'[\d]+ [A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd),?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}|(?:[A-Za-z\s]+,?\s*[A-Z]{2})', snippet)
            if address_match and not details['address']:
                details['address'] = address_match.group().strip()
            
            # Hours (e.g., "Mon–Fri 6:00 AM to 6:00 PM")
            hours_match = re.search(r'(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\s*[-–]\s*(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\s*\d{1,2}:\d{2}\s*(?:AM|PM)\s*to\s*\d{1,2}:\d{2}\s*(?:AM|PM)', snippet, re.IGNORECASE)
            if hours_match and not details['hours']:
                details['hours'] = hours_match.group()
            
            # Website
            if not details['website']:
                details['website'] = item.get('link')
        
        # Fallback: Check website content for address (basic attempt)
        if not details['address'] and details['website']:
            try:
                website_response = requests.get(details['website'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                website_soup = BeautifulSoup(website_response.text, 'html.parser')
                address_tag = website_soup.find('address') or website_soup.find(string=re.compile(r'[A-Za-z\s]+, [A-Z]{2} \d{5}'))
                if address_tag:
                    details['address'] = address_tag.get_text().strip() if isinstance(address_tag, str) else address_tag.strip()
            except Exception:
                pass  # Skip if website fails
        
        return details
        
    except Exception as e:
        return {'error': f'Search failed: {str(e)}'}

if __name__ == '__main__':
    # Test
    result = lookup_organization("Curry N Crust")
    print(f"Curry N Crust Details: {result}")
    result = lookup_organization("Arizona State University")
    print(f"ASU Details: {result}")
    result = lookup_organization("Venezia's Pizza")
    print(f"Venezia's Pizza Details: {result}")