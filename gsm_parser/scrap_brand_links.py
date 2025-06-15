import requests
from bs4 import BeautifulSoup

url = "https://www.gsmarena.com/makers.php3"

response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

brand_links = []

# Находим все таблицы с брендами
tables = soup.find_all('table')
for table in tables:
    links = table.find_all('a')
    for link in links:
        href = link.get('href')
        if href and 'php' in href:
            full_url = f"https://www.gsmarena.com/{href}"
            brand_links.append(full_url)

# Сохраняем ссылки в файл
with open('brand_links.txt', 'w') as f:
    for link in brand_links:
        f.write(link + '\n')

print(f"Saved {len(brand_links)} brand links")
