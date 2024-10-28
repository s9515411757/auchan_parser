import json
import requests
import time

from bs4 import BeautifulSoup
from functools import wraps


def retry(attempts, delay=3, backoff=2):
    """
    Декоратор, который повторно вызывает функцию в случае ошибок.

    Args:
        attempts (int): Количество попыток.
        delay (int, optional): Задержка.
        backoff (int, optional): Множитель задержки.

    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global delay
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts:
                        raise  # Raise the exception if all attempts failed
                    print(f"Ошибка: {e}. Попытка {attempt} из {attempts}.")
                    time.sleep(delay)
                    delay *= backoff
        return wrapper
    return decorator


class AuchanParse:
    def __init__(self, url: str, pages: int = 1, country_mapping: dict = {'Москва': '1'}) -> None:
        """
        Инициализируем переменные.

        Args:
            url (str): Ссылка на каталог.
            pages (int): Кол-во страниц.
            coutry (str): Город.

        """
        self.url = url
        self.pages = pages
        self.country_mapping = country_mapping

        self.data_json = []
        self.params = {}

        self.session = requests.Session()

        self.cookies = {
            'region_id': '1'
        }
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,'
                      'application/xml;q=0.9,image/avif,image/webp,image/apng,*/'
                      '*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'If-None-Match': 'W/"492bec-jEwuo6Kc6wTb+am3EAvIZZNhZTY"',
            'Referer': self.url,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }

    @retry(attempts=3, delay=1, backoff=2)
    def brand_get(self, url: str) -> str:
        """
        Получаем бренд на странице товара.

        Args:
            url (str): Ссылка на каталог.

        """
        response = self.session.get(url)
        html = BeautifulSoup(response.text, "html.parser")
        for row in html.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if th.text == 'Бренд':
                return td.text

        return 'None'

    def cards_get(self, div_card: BeautifulSoup) -> None:
        """
        Получаем список карточек товаров.

        Args:
            div_card (BeautifulSoup): Объект BeautifulSoup

        """
        for data in div_card:
            self.data_json.append(
                {
                    'product ID': data['data-offer-id'],
                    'name': data.find('p', class_='css-1bdovxp').text,
                    'product link': 'https://www.auchan.ru' + data.find(
                        'a',
                        class_='linkToPDP active css-do8div'
                    )['href'],
                    'regular price': data.find('div', class_='active css-xtv3eo').text,
                    'promo price': data.find('div', class_='active css-1hxq85i').text,
                    'brand': self.brand_get('https://www.auchan.ru' + data.find(
                        'a',
                        class_='linkToPDP active css-do8div')['href']
                    )
                }
            )
            print(self.data_json[-1])

    def get_data_json(self):
        """
        Выводим результат.
        """
        return self.data_json

    @retry(attempts=3, delay=1, backoff=2)
    def __enter__(self):
        """
        Проходим по страницам сайта.

        """
        for country_id in self.country_mapping.values():
            print(country_id)
            self.cookies['region_id'] = country_id
            for page in range(1, self.pages + 1):
                self.params['page'] = page

                response = self.session.get(
                    self.url,
                    cookies=self.cookies,
                    headers=self.headers,
                    params=self.params
                )

                html_auchan = BeautifulSoup(response.text, "html.parser")
                div_card = html_auchan.findAll('div', class_='css-n9ebcy-Item')
                self.cards_get(div_card)

        return self

    def __exit__(self, exc_type, exc_val, traceback) -> None:
        """
        Закрываем активную ссессию.
        """
        self.session.close()


def main():
    url = 'https://www.auchan.ru/catalog/sobstvennye-marki-ashan/'
    pages = 1
    country_mapping = {
        'Москва': '1',
        'Санкт-Петербург': '2'
    }

    with AuchanParse(url, pages, country_mapping) as f:
        data_json = f.get_data_json()
        print(len(data_json))
        with open('auchan.json', 'w', encoding='utf-8') as file:
            json.dump(data_json, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
