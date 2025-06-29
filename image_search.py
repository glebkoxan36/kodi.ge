import os
import requests
from flask import current_app

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
        current_app.logger.error(f"Image search error: {str(e)}")
        return PLACEHOLDER

def search_wikimedia_image(phone_name):
    """Поиск изображения через Wikimedia Commons API"""
    try:
        query = f"{phone_name} smartphone"
        url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={query}&srlimit=1&format=json"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'query' in data and 'search' in data['query'] and data['query']['search']:
            page_id = data['query']['search'][0]['pageid']
            
            # Получаем информацию об изображении
            image_url = f"https://commons.wikimedia.org/w/api.php?action=query&pageids={page_id}&prop=imageinfo&iiprop=url&format=json"
            img_response = requests.get(image_url, timeout=10)
            img_data = img_response.json()
            
            if 'query' in img_data and 'pages' in img_data['query']:
                page = img_data['query']['pages'][str(page_id)]
                if 'imageinfo' in page and page['imageinfo']:
                    return page['imageinfo'][0]['url']
        return None
    except Exception as e:
        current_app.logger.error(f"Wikimedia image search error: {str(e)}")
        return None

def search_duckduckgo_image(phone_name):
    """Поиск изображения через неофициальный DuckDuckGo API"""
    try:
        url = "https://duckduckgo.com/"
        params = {
            'q': f"{phone_name} smartphone",
            'iax': 'images',
            'ia': 'images'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Получаем перенаправление
        response = requests.get(url, params=params, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем изображения в результатах
        image_results = soup.select('.tile--img__img')
        if image_results:
            return image_results[0].get('src')
            
        return None
    except Exception as e:
        current_app.logger.error(f"DuckDuckGo image search error: {str(e)}")
        return None

def search_google_direct_image(phone_name):
    """Поиск изображения через прямое обращение к Google Images"""
    try:
        url = "https://www.google.com/search"
        params = {
            'tbm': 'isch',
            'q': f"{phone_name} smartphone"
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
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
    except Exception as e:
        current_app.logger.error(f"Google direct image search error: {str(e)}")
        return None
