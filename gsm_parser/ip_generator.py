import requests
from bs4 import BeautifulSoup

url = "https://sslproxies.org/"

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

proxies = []

# Парсим таблицу с прокси
table = soup.find('table', class_='table table-striped table-bordered')
if table:
    rows = table.find_all('tr')[1:20]  # Берем первые 20
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 2:
            ip = cols[0].text
            port = cols[1].text
            proxy = f"http://{ip}:{port}"
            proxies.append(proxy)

# Сохраняем в файл
with open('ip_addresses.txt', 'w') as f:
    for proxy in proxies:
        f.write(proxy + '\n')

print(f"Saved {len(proxies)} proxies")
