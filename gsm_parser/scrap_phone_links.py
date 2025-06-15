import requests
from bs4 import BeautifulSoup
import re
import time
import random

# Загрузка ссылок на бренды
with open('brand_links.txt', 'r') as f:
    brand_links = [line.strip() for line in f]

phone_links = []

for brand_url in brand_links:
    print(f"Processing {brand_url}")
    page_num = 1
    has_pages = True
    
    while has_pages:
        url = f"{brand_url}"
        if page_num > 1:
            url = url.replace('.php', f'-f-{page_num}-0.php')
        
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим все ссылки на телефоны
            links = soup.find_all('a', href=re.compile(r'\.php$'))
            for link in links:
                href = link.get('href')
                if href and re.search(r'-\d+\.php$', href):
                    full_url = f"https://www.gsmarena.com/{href}"
                    if full_url not in phone_links:
                        phone_links.append(full_url)
                        print(f"Found phone: {full_url}")
            
            # Проверяем наличие следующей страницы
            next_page = soup.find('a', class_='pages-next')
            if next_page:
                page_num += 1
            else:
                has_pages = False
                
            # Случайная пауза
            time.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            has_pages = False

# Сохраняем ссылки в файл
with open('phone_links.txt', 'w') as f:
    for link in phone_links:
        f.write(link + '\n')

print(f"Saved {len(phone_links)} phone links")
