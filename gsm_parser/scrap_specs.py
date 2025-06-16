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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gsm_parser')

def is_gsmarena_available():
    """Проверяет доступность GSMArena с улучшенной диагностикой"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 12; SM-S906N Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/80.0.3987.119 Mobile Safari/537.36'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Попробуем с проверкой SSL
        response = requests.get(
            "https://www.gsmarena.com",
            headers=headers,
            timeout=20,
            allow_redirects=True
        )
        
        if response.status_code == 200:
            return True
        
        # Детальная диагностика статус-кодов
        logger.warning(f"GSMArena returned status code: {response.status_code}")
        
        # Проверка Cloudflare блокировки
        if response.status_code in [403, 429] and 'cf-ray' in response.headers:
            logger.error("Blocked by Cloudflare protection")
            
        # Проверка редиректов
        if response.history:
            redirect_chain = [f"{r.status_code} -> {r.url}" for r in response.history]
            logger.warning(f"Redirect chain: {' | '.join(redirect_chain)}")
            logger.warning(f"Final URL: {response.url}")
            
        return False
        
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL error: {str(e)}")
        # Попытка обойти проблемы с SSL
        try:
            logger.warning("Trying without SSL verification...")
            response = requests.get(
                "https://www.gsmarena.com",
                headers=headers,
                timeout=20,
                verify=False  # Небезопасно, но для диагностики
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
        # Детальный лог исключений
        logger.error(f"GSMArena availability check failed: {type(e).__name__}: {str(e)}")
        return False

def get_fresh_proxies():
    """Получает свежий список HTTPS-прокси с SSLProxies.org"""
    try:
        url = "https://sslproxies.org/"
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        proxies = []
        table = soup.find('table', class_='table table-striped table-bordered')
        if table:
            rows = table.find_all('tr')[1:20]  # Берем первые 20
            for row in rows:
                cols = row.find_all('td')
                # Проверяем наличие 7 колонок и значение 'yes' в колонке HTTPS
                if len(cols) >= 7 and cols[6].text.strip().lower() == 'yes':
                    ip = cols[0].text
                    port = cols[1].text
                    proxy = f"http://{ip}:{port}"
                    proxies.append(proxy)
        
        # Сохраняем в файл только HTTPS-прокси
        with open('ip_addresses.txt', 'w') as f:
            for proxy in proxies:
                f.write(proxy + '\n')
        
        logger.info(f"Fetched {len(proxies)} fresh HTTPS proxies")
        return [{'http': p, 'https': p} for p in proxies]
    
    except Exception as e:
        logger.error(f"Error fetching fresh proxies: {str(e)}")
        return []

def get_proxies():
    """Возвращает список рабочих HTTPS-прокси или пустой список"""
    try:
        # Пытаемся получить свежие HTTPS-прокси
        fresh_proxies = get_fresh_proxies()
        if fresh_proxies:
            return fresh_proxies
            
        # Если не получилось, пробуем загрузить из файла
        if os.path.exists('ip_addresses.txt'):
            with open('ip_addresses.txt', 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
                if proxies:
                    return [{'http': p, 'https': p} for p in proxies]
                    
    except Exception as e:
        logger.error(f"Error loading proxies: {str(e)}")
    
    logger.warning("No HTTPS proxies available")
    return []  # Возвращаем пустой список вместо [None]

def get_db_connection(uri):
    """Устанавливает соединение с MongoDB"""
    client = MongoClient(uri)
    db = client['imei_checker']
    return db['phones'], db['parser_logs']

def scrape_phone_details(url, proxy=None):
    """Собирает детали телефона со страницы"""
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
            
            # Упрощенная обработка прокси
            proxy_config = proxy if proxy is not None else None
            
            response = requests.get(
                url, 
                headers=headers, 
                proxies=proxy_config,
                timeout=45  # Увеличенный таймаут
            )
            
            # Проверка на Cloudflare challenge
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
            
            # Основная информация
            name = soup.find('h1', class_='specs-phone-name-title')
            if name:
                name = name.text.strip()
                brand = re.search(r'^[^\s]+', name).group(0) if name else "Unknown"
            else:
                name = "Unknown"
                brand = "Unknown"
            
            # Спецификации
            specs = {}
            specs_table = soup.find('table', id='specs-list')
            if specs_table:
                current_category = ""
                for row in specs_table.find_all('tr'):
                    # Обработка категорий
                    if row.get('class') and 'section-header' in row.get('class'):
                        current_category = row.find('td').text.strip()
                        specs[current_category] = {}
                    # Обработка спецификаций
                    elif 'ttl' in row.get('class', []):
                        feature = row.find('td', class_='ttl').text.strip()
                        value_cell = row.find('td', class_='nfo')
                        if value_cell:
                            # Извлекаем текст, очищаем от лишних пробелов
                            value = ' '.join(value_cell.text.strip().split())
                            specs.setdefault(current_category, {})[feature] = value
            
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
    """Основная функция парсера"""
    logger.info("Starting GSM Arena parser")
    
    # Добавляем задержку перед проверкой доступности
    logger.info("Waiting 5 seconds before availability check...")
    time.sleep(5)
    
    if not is_gsmarena_available():
        logger.error("GSMArena is not available. Aborting parser.")
        return
    
    phones_collection, logs_collection = get_db_connection(mongodb_uri)
    proxies = get_proxies()  # Может вернуть пустой список
    
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
        # Выбираем случайный прокси если они есть, иначе None
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
            
            # Пауза для избежания блокировки
            sleep_time = random.uniform(5.0, 15.0)  # Увеличенный диапазон пауз
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
            time.sleep(20)  # Большая пауза при ошибке
    
    logger.info("Parser finished successfully")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scrap_specs.py <MONGODB_URI>")
        sys.exit(1)
    
    # Отключаем предупреждения о SSL при использовании verify=False
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main(sys.argv[1])
