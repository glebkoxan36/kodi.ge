import os
import requests

class TechSpecsAPI:
    BASE_URL = "https://api.techspecs.io/v5"
    
    def __init__(self, api_id, api_key):
        self.api_id = api_id
        self.api_key = api_key
        self.headers = {
            "accept": "application/json",
            "X-API-ID": self.api_id,
            "X-API-KEY": self.api_key
        }
    
    def _make_request(self, endpoint, params=None):
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
        except ValueError as e:
            print(f"JSON decode error: {e}")
            return None
    
    def product_search(self, query, keep_casing=True, page=0, size=10):
        endpoint = "/products/search"
        params = {
            "query": query,
            "keepCasing": str(keep_casing).lower(),
            "page": page,
            "size": size
        }
        return self._make_request(endpoint, params)
    
    def get_product_by_id(self, product_id):
        endpoint = f"/products/{product_id}"
        return self._make_request(endpoint)
    
    def get_product_images(self, product_id):
        endpoint = f"/products/{product_id}/images"
        return self._make_request(endpoint)

# Инициализация API с ключами из переменных окружения
api_id = os.getenv('TECHSPECS_API_ID')
api_key = os.getenv('TECHSPECS_API_KEY')

if not api_id or not api_key:
    raise ValueError("TECHSPECS_API_ID and TECHSPECS_API_KEY must be set in environment variables")

api = TechSpecsAPI(api_id, api_key)

def search_phones(query, size=10):
    """Поиск телефонов по запросу"""
    results = api.product_search(query, size=size)
    if results and 'items' in results:
        return results['items']
    return []

def get_phone_details(phone_id):
    """Получение деталей телефона по ID"""
    product = api.get_product_by_id(phone_id)
    if not product:
        return None
    
    images = api.get_product_images(phone_id)
    if isinstance(images, list):
        product['images'] = images
    else:
        product['images'] = []
    
    return product
