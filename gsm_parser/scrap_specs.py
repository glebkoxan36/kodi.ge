
import os
import sys
import requests
import time
import random
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from pymongo import MongoClient
import re
import cloudscraper  # ÐÐ¾Ð²Ñ‹Ð¹ Ð¸Ð¼Ð¿Ð¾Ñ€Ñ‚

# ÐÐ°ÑÑ‚Ñ€Ð¾Ð¹ÐºÐ° Ð»Ð¾Ð³Ð¸Ñ€Ð¾Ð²Ð°Ð½Ð¸Ñ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gsm_parser')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36'
]

def get_proxies():
    # ÐŸÑ€Ð¸Ð¼ÐµÑ€: Ñ‡Ð¸Ñ‚Ð°ÐµÐ¼ ÑÐ¿Ð¸ÑÐ¾Ðº Ð¸Ð· Ñ„Ð°Ð¹Ð»Ð° Ð¸Ð»Ð¸ API. Ð—Ð´ÐµÑÑŒ Ð·Ð°Ð³Ð»ÑƒÑˆÐºÐ°.
    return [
        {'http': 'http://proxy1.example.com:8080', 'https': 'http://proxy1.example.com:8080'},
        {'http': 'http://proxy2.example.com:8080', 'https': 'http://proxy2.example.com:8080'},
    ]

def is_gsmarena_available():
    proxies = get_proxies()
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }

    wait = random.randint(10, 20)
    logger.info(f"Ð–Ð´Ñ‘Ð¼ {wait} ÑÐµÐºÑƒÐ½Ð´ Ð¿ÐµÑ€ÐµÐ´ Ð½Ð°Ñ‡Ð°Ð»Ð¾Ð¼ Ð¿Ñ€Ð¾Ð²ÐµÑ€ÐºÐ¸ Ð´Ð¾ÑÑ‚ÑƒÐ¿Ð½Ð¾ÑÑ‚Ð¸...")
    time.sleep(wait)

    for attempt in range(3):
        proxy_cfg = random.choice(proxies) if proxies else None
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get("https://www.gsmarena.com", headers=headers, proxies=proxy_cfg, timeout=20)

            if resp.status_code == 200:
                logger.info("GSMArena Ð´Ð¾ÑÑ‚ÑƒÐ¿ÐµÐ½.")
                return True
            elif resp.status_code == 429:
                delay = (2 ** attempt) + random.uniform(1, 3)
                logger.warning(f"429 Too Many Requests. Ð–Ð´Ñ‘Ð¼ {delay:.1f} ÑÐµÐºÑƒÐ½Ð´ Ð¸ Ð¿Ñ€Ð¾Ð±ÑƒÐµÐ¼ ÑÐ½Ð¾Ð²Ð°...")
                time.sleep(delay)
            else:
                logger.warning(f"ÐÐµÐ¾Ð¶Ð¸Ð´Ð°Ð½Ð½Ñ‹Ð¹ ÑÑ‚Ð°Ñ‚ÑƒÑ {resp.status_code} Ð¿Ñ€Ð¸ Ð¿Ñ€Ð¾Ð²ÐµÑ€ÐºÐµ Ð´Ð¾ÑÑ‚ÑƒÐ¿Ð½Ð¾ÑÑ‚Ð¸.")
        except Exception as e:
            logger.warning(f"ÐžÑˆÐ¸Ð±ÐºÐ° ÑÐ¾ÐµÐ´Ð¸Ð½ÐµÐ½Ð¸Ñ Ñ Ð¿Ñ€Ð¾ÐºÑÐ¸ {proxy_cfg}: {e}")
    return False


import os
import sys
import requests
import time
import random
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from pymongo import MongoClient
import re

# ÐÐ°ÑÑ‚Ñ€Ð¾Ð¹ÐºÐ° Ð»Ð¾Ð³Ð¸Ñ€Ð¾Ð²Ð°Ð½Ð¸Ñ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gsm_parser')

            logger.warning("Trying without SSL verification...")
            response = requests.get(
                "https://www.gsmarena.com",
                headers=headers,
                timeout=20,
                verify=False  # ÐÐµÐ±ÐµÐ·Ð¾Ð¿Ð°ÑÐ½Ð¾, Ð½Ð¾ Ð´Ð»Ñ Ð´Ð¸Ð°Ð³Ð½Ð¾ÑÑ‚Ð¸ÐºÐ¸
            )
            return response.status_code == 200
        except Exception as ssl_fallback_error:
            logger.error(f"SSL fallback failed: {str(ssl_fallback_error)}")
            return False
        
    except requests.exceptions.Timeout:
        logger.error("Connection to GSMArena timed out")
        return False
        
    except requests.exceptions.ConnectionError as ce:
        logger.error(f"Connection error: {str(ce)}")
        return False
        
    except Exception as e:
        # Ð”ÐµÑ‚Ð°Ð»ÑŒÐ½Ñ‹Ð¹ Ð»Ð¾Ð³ Ð¸ÑÐºÐ»ÑŽÑ‡ÐµÐ½Ð¸Ð¹
        logger.error(f"GSMArena availability check failed: {type(e).__name__}: {str(e)}")
        return False

def get_fresh_proxies():
    """ÐŸÐ¾Ð»ÑƒÑ‡Ð°ÐµÑ‚ ÑÐ²ÐµÐ¶Ð¸Ð¹ ÑÐ¿Ð¸ÑÐ¾Ðº HTTPS-Ð¿Ñ€Ð¾ÐºÑÐ¸ Ñ SSLProxies.org"""
    try:
        url = "https://sslproxies.org/"
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        proxies = []
        table = soup.find('table', class_='table table-striped table-bordered')
        if table:
            rows = table.find_all('tr')[1:20]  # Ð‘ÐµÑ€ÐµÐ¼ Ð¿ÐµÑ€Ð²Ñ‹Ðµ 20
            for row in rows:
                cols = row.find_all('td')
                # ÐŸÑ€Ð¾Ð²ÐµÑ€ÑÐµÐ¼ Ð½Ð°Ð»Ð¸Ñ‡Ð¸Ðµ 7 ÐºÐ¾Ð»Ð¾Ð½Ð¾Ðº Ð¸ Ð·Ð½Ð°Ñ‡ÐµÐ½Ð¸Ðµ 'yes' Ð² ÐºÐ¾Ð»Ð¾Ð½ÐºÐµ HTTPS
                if len(cols) >= 7 and cols[6].text.strip().lower() == 'yes':
                    ip = cols[0].text
                    port = cols[1].text
                    proxy = f"http://{ip}:{port}"
                    proxies.append(proxy)
        
        # Ð¡Ð¾Ñ…Ñ€Ð°Ð½ÑÐµÐ¼ Ð² Ñ„Ð°Ð¹Ð» Ñ‚Ð¾Ð»ÑŒÐºÐ¾ HTTPS-Ð¿Ñ€Ð¾ÐºÑÐ¸
        with open('ip_addresses.txt', 'w') as f:
            for proxy in proxies:
                f.write(proxy + '\n')
        
        logger.info(f"Fetched {len(proxies)} fresh HTTPS proxies")
        return [{'http': p, 'https': p} for p in proxies]
    
    except Exception as e:
        logger.error(f"Error fetching fresh proxies: {str(e)}")
        return []

def get_proxies():
    """Ð’Ð¾Ð·Ð²Ñ€Ð°Ñ‰Ð°ÐµÑ‚ ÑÐ¿Ð¸ÑÐ¾Ðº Ñ€Ð°Ð±Ð¾Ñ‡Ð¸Ñ… HTTPS-Ð¿Ñ€Ð¾ÐºÑÐ¸ Ð¸Ð»Ð¸ Ð¿ÑƒÑÑ‚Ð¾Ð¹ ÑÐ¿Ð¸ÑÐ¾Ðº"""
    try:
        # ÐŸÑ‹Ñ‚Ð°ÐµÐ¼ÑÑ Ð¿Ð¾Ð»ÑƒÑ‡Ð¸Ñ‚ÑŒ ÑÐ²ÐµÐ¶Ð¸Ðµ HTTPS-Ð¿Ñ€Ð¾ÐºÑÐ¸
        fresh_proxies = get_fresh_proxies()
        if fresh_proxies:
            return fresh_proxies
            
        # Ð•ÑÐ»Ð¸ Ð½Ðµ Ð¿Ð¾Ð»ÑƒÑ‡Ð¸Ð»Ð¾ÑÑŒ, Ð¿Ñ€Ð¾Ð±ÑƒÐµÐ¼ Ð·Ð°Ð³Ñ€ÑƒÐ·Ð¸Ñ‚ÑŒ Ð¸Ð· Ñ„Ð°Ð¹Ð»Ð°
        if os.path.exists('ip_addresses.txt'):
            with open('ip_addresses.txt', 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
                if proxies:
                    return [{'http': p, 'https': p} for p in proxies]
                    
    except Exception as e:
        logger.error(f"Error loading proxies: {str(e)}")
    
    logger.warning("No HTTPS proxies available")
    return []  # Ð’Ð¾Ð·Ð²Ñ€Ð°Ñ‰Ð°ÐµÐ¼ Ð¿ÑƒÑÑ‚Ð¾Ð¹ ÑÐ¿Ð¸ÑÐ¾Ðº Ð²Ð¼ÐµÑÑ‚Ð¾ [None]

def get_db_connection(uri):
    """Ð£ÑÑ‚Ð°Ð½Ð°Ð²Ð»Ð¸Ð²Ð°ÐµÑ‚ ÑÐ¾ÐµÐ´Ð¸Ð½ÐµÐ½Ð¸Ðµ Ñ MongoDB"""
    client = MongoClient(uri)
    db = client['imei_checker']
    return db['phones'], db['parser_logs']

def scrape_phone_details(url, proxy=None):
    """Ð¡Ð¾Ð±Ð¸Ñ€Ð°ÐµÑ‚ Ð´ÐµÑ‚Ð°Ð»Ð¸ Ñ‚ÐµÐ»ÐµÑ„Ð¾Ð½Ð° ÑÐ¾ ÑÑ‚Ñ€Ð°Ð½Ð¸Ñ†Ñ‹"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
                ]),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'DNT': '1',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Ð£Ð¿Ñ€Ð¾Ñ‰ÐµÐ½Ð½Ð°Ñ Ð¾Ð±Ñ€Ð°Ð±Ð¾Ñ‚ÐºÐ° Ð¿Ñ€Ð¾ÐºÑÐ¸
            proxy_config = proxy if proxy is not None else None
            
            response = requests.get(
                url, 
                headers=headers, 
                proxies=proxy_config,
                timeout=45  # Ð£Ð²ÐµÐ»Ð¸Ñ‡ÐµÐ½Ð½Ñ‹Ð¹ Ñ‚Ð°Ð¹Ð¼Ð°ÑƒÑ‚
            )
            
            # ÐŸÑ€Ð¾Ð²ÐµÑ€ÐºÐ° Ð½Ð° Cloudflare challenge
            if "cf-chl-bypass" in response.url:
                logger.error("Cloudflare challenge detected")
                return None
                
            if response.status_code == 429:  # Too Many Requests
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Rate limited for {url}. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
                
            if response.status_code != 200:
                logger.warning(f"Non-200 status code {response.status_code} for {url}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # ÐžÑÐ½Ð¾Ð²Ð½Ð°Ñ Ð¸Ð½Ñ„Ð¾Ñ€Ð¼Ð°Ñ†Ð¸Ñ
            name = soup.find('h1', class_='specs-phone-name-title')
            if name:
                name = name.text.strip()
                brand = re.search(r'^[^\s]+', name).group(0) if name else "Unknown"
            else:
                name = "Unknown"
                brand = "Unknown"
            
            # Ð¡Ð¿ÐµÑ†Ð¸Ñ„Ð¸ÐºÐ°Ñ†Ð¸Ð¸
            specs = {}
            specs_table = soup.find('table', id='specs-list')
            if specs_table:
                current_category = ""
                for row in specs_table.find_all('tr'):
                    # ÐžÐ±Ñ€Ð°Ð±Ð¾Ñ‚ÐºÐ° ÐºÐ°Ñ‚ÐµÐ³Ð¾Ñ€Ð¸Ð¹
                    if row.get('class') and 'section-header' in row.get('class'):
                        current_category = row.find('td').text.strip()
                        specs[current_category] = {}
                    # ÐžÐ±Ñ€Ð°Ð±Ð¾Ñ‚ÐºÐ° ÑÐ¿ÐµÑ†Ð¸Ñ„Ð¸ÐºÐ°Ñ†Ð¸Ð¹
                    elif 'ttl' in row.get('class', []):
                        feature = row.find('td', class_='ttl').text.strip()
                        value_cell = row.find('td', class_='nfo')
                        if value_cell:
                            # Ð˜Ð·Ð²Ð»ÐµÐºÐ°ÐµÐ¼ Ñ‚ÐµÐºÑÑ‚, Ð¾Ñ‡Ð¸Ñ‰Ð°ÐµÐ¼ Ð¾Ñ‚ Ð»Ð¸ÑˆÐ½Ð¸Ñ… Ð¿Ñ€Ð¾Ð±ÐµÐ»Ð¾Ð²
                            value = ' '.join(value_cell.text.strip().split())
                            specs.setdefault(current_category, {})[feature] = value
            
            # Ð”Ð¾Ð¿Ð¾Ð»Ð½Ð¸Ñ‚ÐµÐ»ÑŒÐ½Ð°Ñ Ð¸Ð½Ñ„Ð¾Ñ€Ð¼Ð°Ñ†Ð¸Ñ
            quick_specs = {}
            quick_list = soup.find('div', class_='quick-specs')
            if quick_list:
                for li in quick_list.find_all('li'):
                    text = li.text.strip()
                    if ':' in text:
                        key, value = text.split(':', 1)
                        quick_specs[key.strip()] = value.strip()
            
            # Ð ÐµÐ¹Ñ‚Ð¸Ð½Ð³Ð¸
            rating_elem = soup.find('div', class_='rating-number')
            rating = rating_elem.text.strip() if rating_elem else "N/A"
            
            # Ð˜Ð·Ð¾Ð±Ñ€Ð°Ð¶ÐµÐ½Ð¸Ðµ
            img_elem = soup.find('div', class_='specs-photo-main')
            if img_elem:
                img_elem = img_elem.find('img')
                image_url = img_elem['src'] if img_elem and 'src' in img_elem.attrs else None
            else:
                image_url = None
            
            return {
                'url': url,
                'name': name,
                'brand': brand,
                'model': name.replace(brand, '').strip(),
                'specs': specs,
                'quick_specs': quick_specs,
                'rating': rating,
                'image_url': image_url,
                'scraped_at': datetime.utcnow()
            }
            
        except (requests.exceptions.RequestException, ConnectionError) as e:
            logger.warning(f"Attempt {attempt+1} failed for {url}: {str(e)}")
            time.sleep(3)
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None
    
    logger.error(f"Failed to scrape {url} after {max_retries} attempts")
    return None

def main(mongodb_uri):
    """ÐžÑÐ½Ð¾Ð²Ð½Ð°Ñ Ñ„ÑƒÐ½ÐºÑ†Ð¸Ñ Ð¿Ð°Ñ€ÑÐµÑ€Ð°"""
    logger.info("Starting GSM Arena parser")
    if not is_gsmarena_available():
        logger.error("GSMArena is not available. Aborting parser.")
        return
    
    # Ð”Ð¾Ð±Ð°Ð²Ð»ÑÐµÐ¼ Ð·Ð°Ð´ÐµÑ€Ð¶ÐºÑƒ Ð¿ÐµÑ€ÐµÐ´ Ð¿Ñ€Ð¾Ð²ÐµÑ€ÐºÐ¾Ð¹ Ð´Ð¾ÑÑ‚ÑƒÐ¿Ð½Ð¾ÑÑ‚Ð¸
    logger.info("Waiting 5 seconds before availability check...")
    time.sleep(5)
    
    if not is_gsmarena_available():
        logger.error("GSMArena is not available. Aborting parser.")
        return
    
    phones_collection, logs_collection = get_db_connection(mongodb_uri)
    proxies = get_proxies()  # ÐœÐ¾Ð¶ÐµÑ‚ Ð²ÐµÑ€Ð½ÑƒÑ‚ÑŒ Ð¿ÑƒÑÑ‚Ð¾Ð¹ ÑÐ¿Ð¸ÑÐ¾Ðº
    
    # ÐŸÐ¾Ð»ÑƒÑ‡Ð°ÐµÐ¼ ÑÐ¿Ð¸ÑÐ¾Ðº URL Ñ‚ÐµÐ»ÐµÑ„Ð¾Ð½Ð¾Ð²
    try:
        with open('phone_links.txt', 'r') as f:
            phone_urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error("phone_links.txt not found")
        return
    
    total = len(phone_urls)
    logger.info(f"Found {total} phones to process")
    
    # ÐŸÑ€Ð¾Ð²ÐµÑ€ÑÐµÐ¼, Ñ ÐºÐ°ÐºÐ¾Ð³Ð¾ Ð¼ÐµÑÑ‚Ð° Ð¿Ñ€Ð¾Ð´Ð¾Ð»Ð¶Ð¸Ñ‚ÑŒ
    last_processed = logs_collection.find_one(
        {'status': 'success'}, 
        sort=[('timestamp', -1)]
    )
    start_index = 0
    
    if last_processed:
        try:
            last_url = last_processed['url']
            start_index = phone_urls.index(last_url) + 1
            logger.info(f"Resuming from index {start_index}/{total}")
        except ValueError:
            logger.info("Starting from beginning")
    
    # ÐžÐ±Ñ€Ð°Ð±Ð¾Ñ‚ÐºÐ° ÐºÐ°Ð¶Ð´Ð¾Ð³Ð¾ Ñ‚ÐµÐ»ÐµÑ„Ð¾Ð½Ð°
    for i in range(start_index, total):
        url = phone_urls[i]
        # Ð’Ñ‹Ð±Ð¸Ñ€Ð°ÐµÐ¼ ÑÐ»ÑƒÑ‡Ð°Ð¹Ð½Ñ‹Ð¹ Ð¿Ñ€Ð¾ÐºÑÐ¸ ÐµÑÐ»Ð¸ Ð¾Ð½Ð¸ ÐµÑÑ‚ÑŒ, Ð¸Ð½Ð°Ñ‡Ðµ None
        proxy = random.choice(proxies) if proxies else None
        
        try:
            start_time = time.time()
            phone_data = scrape_phone_details(url, proxy)
            
            if phone_data:
                # Ð¡Ð¾Ñ…Ñ€Ð°Ð½ÑÐµÐ¼ Ð² Ð±Ð°Ð·Ñƒ
                existing = phones_collection.find_one({'url': url})
                if existing:
                    phones_collection.update_one(
                        {'_id': existing['_id']},
                        {'$set': phone_data}
                    )
                    action = "updated"
                else:
                    phones_collection.insert_one(phone_data)
                    action = "inserted"
                
                # Ð›Ð¾Ð³Ð¸Ñ€ÑƒÐµÐ¼ ÑƒÑÐ¿ÐµÑ…
                logs_collection.insert_one({
                    'url': url,
                    'status': 'success',
                    'action': action,
                    'timestamp': datetime.utcnow(),
                    'duration': time.time() - start_time,
                    'phone_name': phone_data.get('name', '')
                })
                
                logger.info(f"[{i+1}/{total}] {action} {phone_data['name']}")
            else:
                logs_collection.insert_one({
                    'url': url,
                    'status': 'error',
                    'error': 'No data scraped',
                    'timestamp': datetime.utcnow()
                })
                logger.warning(f"[{i+1}/{total}] Failed to scrape {url}")
            
            # ÐŸÐ°ÑƒÐ·Ð° Ð´Ð»Ñ Ð¸Ð·Ð±ÐµÐ¶Ð°Ð½Ð¸Ñ Ð±Ð»Ð¾ÐºÐ¸Ñ€Ð¾Ð²ÐºÐ¸
            sleep_time = random.uniform(5.0, 15.0)  # Ð£Ð²ÐµÐ»Ð¸Ñ‡ÐµÐ½Ð½Ñ‹Ð¹ Ð´Ð¸Ð°Ð¿Ð°Ð·Ð¾Ð½ Ð¿Ð°ÑƒÐ·
            logger.info(f"Waiting {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
            
        except Exception as e:
            logs_collection.insert_one({
                'url': url,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow()
            })
            logger.error(f"[{i+1}/{total}] Error processing {url}: {str(e)}")
            time.sleep(20)  # Ð‘Ð¾Ð»ÑŒÑˆÐ°Ñ Ð¿Ð°ÑƒÐ·Ð° Ð¿Ñ€Ð¸ Ð¾ÑˆÐ¸Ð±ÐºÐµ
    
    logger.info("Parser finished successfully")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scrap_specs.py <MONGODB_URI>")
        sys.exit(1)
    
    # ÐžÑ‚ÐºÐ»ÑŽÑ‡Ð°ÐµÐ¼ Ð¿Ñ€ÐµÐ´ÑƒÐ¿Ñ€ÐµÐ¶Ð´ÐµÐ½Ð¸Ñ Ð¾ SSL Ð¿Ñ€Ð¸ Ð¸ÑÐ¿Ð¾Ð»ÑŒÐ·Ð¾Ð²Ð°Ð½Ð¸Ð¸ verify=False
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main(sys.argv[1])
