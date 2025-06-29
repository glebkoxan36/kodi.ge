import os
import requests
from flask import current_app
from bs4 import BeautifulSoup
import urllib.parse
from requests.exceptions import RequestException, Timeout, ConnectionError, JSONDecodeError

PLACEHOLDER = '/static/placeholder.jpg'

def search_phone_image(phone_name):
    """Ищет изображение телефона через Wikimedia API и резервные источники"""
    try:
        # Попытка 1: Поиск через Wikimedia API
        image_url = search_wikimedia_image(phone_name)
        if image_url:
            return image_url
        
        # Попытка 2: Поиск через DuckDuckGo (неофициальный API)
        image_url = search_duckduckgo_image(phone_name)
        if image_url:
            return image_url
        
        # Попытка 3: Поиск через Google (без API)
        image_url = search_google_direct_image(phone_name)
        if image_url:
            return image_url
            
        return PLACEHOLDER
    except Exception as e:
        current_app.logger.error(f"General image search error: {str(e)}", exc_info=True)
        return PLACEHOLDER

def search_wikimedia_image(phone_name):
    """Поиск изображения через Wikimedia Commons API"""
    try:
        query = f"{phone_name} smartphone"
        base_url = "https://commons.wikimedia.org/w/api.php"
        
        # Параметры первого запроса (поиск)
        search_params = {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'srlimit': 1,
            'srnamespace': 6,
            'format': 'json'
        }
        
        # Выполняем запрос с кодированными параметрами
        response = requests.get(
            base_url,
            params=search_params,
            timeout=(3.05, 10),  # Таймаут подключения и чтения
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0'}
        )
        
        # Проверяем статус и наличие контента
        if response.status_code != 200:
            current_app.logger.error(f"Wikimedia HTTP error: {response.status_code}")
            return None
        
        # Проверяем валидность JSON
        try:
            data = response.json()
        except JSONDecodeError:
            current_app.logger.error("Wikimedia returned invalid JSON")
            return None
        
        # Обрабатываем результаты поиска
        if not data.get('query', {}).get('search'):
            return None
            
        page_id = data['query']['search'][0]['pageid']
        
        # Параметры второго запроса (информация об изображении)
        image_params = {
            'action': 'query',
            'pageids': page_id,
            'prop': 'imageinfo',
            'iiprop': 'url',
            'format': 'json'
        }
        
        img_response = requests.get(
            base_url,
            params=image_params,
            timeout=(3.05, 10),
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0'}
        )
        
        if img_response.status_code != 200:
            return None
            
        try:
            img_data = img_response.json()
        except JSONDecodeError:
            return None
            
        # Извлекаем URL изображения
        pages = img_data.get('query', {}).get('pages', {})
        if pages and str(page_id) in pages:
            image_info = pages[str(page_id)].get('imageinfo', [])
            if image_info:
                return image_info[0]['url']
                
        return None
        
    except (Timeout, ConnectionError) as e:
        current_app.logger.warning(f"Wikimedia network error: {str(e)}")
        return None
    except Exception as e:
        current_app.logger.error(f"Wikimedia image search error: {str(e)}", exc_info=True)
        return None

def search_duckduckgo_image(phone_name):
    """Поиск изображения через неофициальный DuckDuckGo API"""
    try:
        base_url = "https://duckduckgo.com/"
        params = {
            'q': f"{phone_name} smartphone",
            'iax': 'images',
            'ia': 'images'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(
            base_url,
            params=params,
            headers=headers,
            timeout=(3.05, 10)
        )
        
        if response.status_code != 200:
            current_app.logger.warning(f"DuckDuckGo HTTP error: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем изображения в результатах
        image_results = soup.select('.tile--img__img')
        if image_results:
            return image_results[0].get('src')
            
        return None
        
    except (Timeout, ConnectionError) as e:
        current_app.logger.warning(f"DuckDuckGo network error: {str(e)}")
        return None
    except Exception as e:
        current_app.logger.error(f"DuckDuckGo image search error: {str(e)}", exc_info=True)
        return None

def search_google_direct_image(phone_name):
    """Поиск изображения через прямое обращение к Google Images"""
    try:
        base_url = "https://www.google.com/search"
        params = {
            'tbm': 'isch',
            'q': f"{phone_name} smartphone"
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(
            base_url,
            params=params,
            headers=headers,
            timeout=(3.05, 10)
        )
        
        if response.status_code != 200:
            current_app.logger.warning(f"Google HTTP error: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем изображения в результатах
        image_results = soup.select('img[src^="http"]')
        if image_results:
            # Пропускаем логотипы и иконки
            for img in image_results:
                src = img.get('src')
                if src and 'logo' not in src and 'icon' not in src:
                    return src
                    
        return None
        
    except (Timeout, ConnectionError) as e:
        current_app.logger.warning(f"Google network error: {str(e)}")
        return None
    except Exception as e:
        current_app.logger.error(f"Google direct image search error: {str(e)}", exc_info=True)
        return None
