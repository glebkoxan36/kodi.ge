import os
import sys
import requests
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pymongo import MongoClient
from datetime import datetime
import logging
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gsm_parser')

def get_proxies():
    """Возвращает список прокси из файла или генерирует новые"""
    try:
        with open('ip_addresses.txt', 'r') as f:
            proxies = f.read().splitlines()
            return [{'http': p, 'https': p} for p in proxies if p.strip()]
    except:
        logger.error("Proxy file not found, using no proxies")
        return [None]

def get_db_connection(uri):
    client = MongoClient(uri)
    db = client['imei_checker']
    return db['phones'], db['parser_logs']

def scrape_phone_details(url, proxy=None):
    """Собирает детали телефона со страницы"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, proxies=proxy, timeout=30)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Основная информация
        name = soup.find('h1', class_='specs-phone-name-title').text.strip()
        brand = re.search(r'^[^\s]+', name).group(0)
        
        # Основные характеристики
        specs = {}
        specs_table = soup.find('table', id='specs-list')
        for row in specs_table.find_all('tr'):
            if 'ttl' in row.get('class', []) and 'nfo' in row.get('class', []):
                continue
                
            if 'ttl' in row.get('class', []):
                key = row.text.strip()
                value_row = row.find_next_sibling('tr')
                if value_row and 'nfo' in value_row.get('class', []):
                    value = value_row.text.strip()
                    specs[key] = value
        
        # Дополнительная информация
        quick_specs = {}
        quick_list = soup.find('div', class_='quick-specs')
        if quick_list:
            for li in quick_list.find_all('li'):
                text = li.text.strip()
                if ':' in text:
                    key, value = text.split(':', 1)
                    quick_specs[key.strip()] = value.strip()
        
        # Рейтинги
        rating_elem = soup.find('div', class_='rating-number')
        rating = rating_elem.text.strip() if rating_elem else "N/A"
        
        # Изображение
        img_elem = soup.find('div', class_='specs-photo-main').find('img')
        image_url = img_elem['src'] if img_elem else None
        
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
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return None

def main(mongodb_uri):
    logger.info("Starting GSM Arena parser")
    
    phones_collection, logs_collection = get_db_connection(mongodb_uri)
    proxies = get_proxies()
    
    # Получаем список URL телефонов
    try:
        with open('phone_links.txt', 'r') as f:
            phone_urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error("phone_links.txt not found")
        return
    
    total = len(phone_urls)
    logger.info(f"Found {total} phones to process")
    
    # Проверяем, с какого места продолжить
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
    
    # Обработка каждого телефона
    for i in range(start_index, total):
        url = phone_urls[i]
        proxy = random.choice(proxies) if proxies else None
        
        try:
            start_time = time.time()
            phone_data = scrape_phone_details(url, proxy)
            
            if phone_data:
                # Сохраняем в базу
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
                
                # Логируем успех
                logs_collection.insert_one({
                    'url': url,
                    'status': 'success',
                    'action': action,
                    'timestamp': datetime.utcnow(),
                    'duration': time.time() - start_time
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
            
            # Пауза для избежания блокировки
            time.sleep(random.uniform(1.0, 3.0))
            
        except Exception as e:
            logs_collection.insert_one({
                'url': url,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow()
            })
            logger.error(f"[{i+1}/{total}] Error processing {url}: {str(e)}")
            time.sleep(5)  # Большая пауза при ошибке
    
    logger.info("Parser finished successfully")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scrap_specs.py <MONGODB_URI>")
        sys.exit(1)
    main(sys.argv[1])
