import requests
from urllib.parse import quote

class TechSpecsAPI:
    BASE_URL = "https://api.techspecs.io/v5"
    
    def __init__(self, api_id, api_key):
        self.api_id = api_id
        self.api_key = api_key
        self.headers = {
            "accept": "application/json",
            "x-api-id": self.api_id,
            "x-api-key": self.api_key
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
    
    # Product Endpoints
    def product_search(self, query, keep_casing=True, page=0, size=10):
        endpoint = "/products/search"
        params = {
            "query": query,
            "keepCasing": str(keep_casing).lower(),
            "page": page,
            "size": size
        }
        return self._make_request(endpoint, params)
    
    def get_product_schemas(self):
        endpoint = "/products/schemas"
        return self._make_request(endpoint)
    
    def get_product_by_id(self, product_id):
        endpoint = f"/products/{product_id}"
        return self._make_request(endpoint)
    
    def get_product_images(self, product_id):
        endpoint = f"/products/{product_id}/images"
        return self._make_request(endpoint)
    
    # Brand Endpoints
    def get_brands(self):
        endpoint = "/brands"
        return self._make_request(endpoint)
    
    def get_brand_logos(self):
        endpoint = "/brand-logos"
        return self._make_request(endpoint)
    
    # Category Endpoints
    def get_categories(self):
        endpoint = "/categories"
        return self._make_request(endpoint)


# Пример использования
if __name__ == "__main__":
    # Инициализация API с вашими ключами
    api = TechSpecsAPI(
        api_id="68625f85b363e86de2ae7e0a",
        api_key="35a39ff6-545c-44e7-9861-f0c3eed6dcb4"
    )
    
    # Примеры запросов
    print("=== Product Search ===")
    search_results = api.product_search("iPhone 14", size=3)
    print(search_results)
    
    print("\n=== Product Details ===")
    if search_results and 'items' in search_results and len(search_results['items']) > 0:
        first_product_id = search_results['items'][0]['id']
        product_details = api.get_product_by_id(first_product_id)
        print(f"Product Name: {product_details['data']['name']}")
        
        images = api.get_product_images(first_product_id)
        print(f"Images Count: {len(images)}")
    
    print("\n=== Brands ===")
    brands = api.get_brands()
    print(f"Total Brands: {len(brands)}")
    
    print("\n=== Categories ===")
    categories = api.get_categories()
    print(f"Total Categories: {len(categories)}")
