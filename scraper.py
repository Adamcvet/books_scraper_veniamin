"""Парсер каталога книг с сайта http://books.toscrape.com.

Запуск:
    python scraper.py          # запуск по расписанию каждый день в 19:00
    python scraper.py --now    # однократный сбор данных прямо сейчас
"""

import argparse
import json
import os
import re
import time

import requests
import schedule
from bs4 import BeautifulSoup

BASE_URL = 'http://books.toscrape.com/catalogue/'
PAGE_URL = BASE_URL + 'page-{}.html'
DEFAULT_FILE = os.path.join('artifacts', 'books_data.txt')

# на сайте рейтинг задан словом в классе тега: <p class="star-rating Three">
RATINGS = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}


def get_soup(url: str, session: requests.Session = None) -> BeautifulSoup:
    """Скачивает страницу и возвращает распарсенный HTML.

    Args:
        url (str): адрес страницы.
        session (requests.Session, optional): сессия для повторного
            использования соединения. Если не передана, запрос делается
            через обычный requests.get.

    Returns:
        BeautifulSoup: объект для поиска элементов на странице.

    Raises:
        requests.HTTPError: если сервер вернул код ошибки (например, 404).
    """
    http = session or requests
    response = http.get(url, timeout=10)
    response.raise_for_status()
    # сайт не указывает кодировку в заголовках, из-за этого
    # вместо "£" получается "Â£", поэтому задаём её явно
    response.encoding = 'utf-8'
    return BeautifulSoup(response.text, 'html.parser')


def get_book_data(book_url: str, session: requests.Session = None) -> dict:
    """Собирает информацию о книге с её страницы.

    Args:
        book_url (str): ссылка на страницу книги, например
            'http://books.toscrape.com/catalogue/
            a-light-in-the-attic_1000/index.html'.
        session (requests.Session, optional): сессия requests, чтобы
            не открывать новое соединение на каждую книгу.

    Returns:
        dict: словарь с данными о книге:
            - title (str): название;
            - category (str): жанр из "хлебных крошек";
            - price (float): цена в фунтах;
            - rating (int): рейтинг от 1 до 5 (0, если не найден);
            - in_stock (int): количество экземпляров в наличии;
            - description (str): описание (пустая строка, если его нет);
            - product_information (dict): таблица Product Information
              (UPC, Product Type, цены с налогом и без, и т.д.);
            - url (str): ссылка на страницу книги.
    """
    soup = get_soup(book_url, session)
    main = soup.find('div', class_='product_main')

    title = main.find('h1').get_text(strip=True)
    price = float(main.find('p', class_='price_color').get_text()[1:])

    rating_tag = main.find('p', class_='star-rating')
    rating = 0
    for cls in rating_tag['class']:
        if cls in RATINGS:
            rating = RATINGS[cls]

    # текст вида "In stock (22 available)" -> 22
    availability = main.find('p', class_='availability').get_text()
    numbers = re.findall(r'\d+', availability)
    in_stock = int(numbers[0]) if numbers else 0

    # описание лежит в первом <p> после блока с id="product_description",
    # у некоторых книг описания нет совсем
    description = ''
    desc_header = soup.find('div', id='product_description')
    if desc_header is not None:
        description = desc_header.find_next_sibling('p').get_text(strip=True)

    product_info = {}
    for row in soup.find('table', class_='table-striped').find_all('tr'):
        key = row.find('th').get_text(strip=True)
        value = row.find('td').get_text(strip=True)
        product_info[key] = value

    breadcrumb = soup.find('ul', class_='breadcrumb').find_all('a')
    category = breadcrumb[-1].get_text(strip=True)

    return {
        'title': title,
        'category': category,
        'price': price,
        'rating': rating,
        'in_stock': in_stock,
        'description': description,
        'product_information': product_info,
        'url': book_url,
    }


def get_book_links(page_url: str, session: requests.Session = None) -> list:
    """Возвращает ссылки на все книги с одной страницы каталога.

    Args:
        page_url (str): адрес страницы каталога вида
            'http://books.toscrape.com/catalogue/page-1.html'.
        session (requests.Session, optional): сессия requests.

    Returns:
        list[str]: список абсолютных ссылок на страницы книг
            (на одной странице каталога 20 книг).
    """
    soup = get_soup(page_url, session)
    links = []
    for book in soup.find_all('article', class_='product_pod'):
        href = book.find('h3').find('a')['href']
        # ссылки относительные: 'a-light-in-the-attic_1000/index.html'
        links.append(BASE_URL + href)
    return links


def save_books(books: list, filename: str = DEFAULT_FILE) -> None:
    """Сохраняет список книг в текстовый файл, одна книга на строку (JSON).

    Args:
        books (list[dict]): данные о книгах.
        filename (str): путь к файлу. Папка создаётся, если её нет.
    """
    folder = os.path.dirname(filename)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        for book in books:
            f.write(json.dumps(book, ensure_ascii=False) + '\n')


def scrape_books(is_save: bool = False, n_pages: int = None,
                 filename: str = DEFAULT_FILE) -> list:
    """Обходит страницы каталога и собирает данные обо всех книгах.

    Страницы перебираются по порядку (page-1.html, page-2.html, ...),
    пока сайт не вернёт ошибку 404 - это значит, что страницы закончились.

    Args:
        is_save (bool): если True, результат сохраняется в файл filename.
        n_pages (int, optional): сколько страниц обойти. По умолчанию
            None - обходятся все страницы (их 50, это 1000 книг).
        filename (str): путь к файлу для сохранения результата.

    Returns:
        list[dict]: список словарей с данными о книгах
            (формат словаря описан в get_book_data).
    """
    books = []
    page = 1
    with requests.Session() as session:
        while n_pages is None or page <= n_pages:
            try:
                links = get_book_links(PAGE_URL.format(page), session)
            except requests.HTTPError:
                break
            for link in links:
                books.append(get_book_data(link, session))
            print(f'Страница {page}: собрано {len(books)} книг')
            page += 1

    if is_save:
        save_books(books, filename)
        print(f'Данные сохранены в {filename}')
    return books


def job() -> None:
    """Задача для планировщика: собрать все книги и сохранить в файл."""
    print(time.strftime('%Y-%m-%d %H:%M:%S'), '- запуск сбора данных')
    scrape_books(is_save=True)


def run_schedule(run_time: str = '19:00', check_every: int = 60) -> None:
    """Запускает сбор данных каждый день в указанное время.

    Args:
        run_time (str): время запуска в формате 'чч:мм'.
        check_every (int): раз во сколько секунд проверять,
            не пора ли запускать задачу.
    """
    schedule.every().day.at(run_time).do(job)
    print(f'Сбор данных запланирован на {run_time} каждый день')
    while True:
        schedule.run_pending()
        time.sleep(check_every)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Парсер books.toscrape.com')
    parser.add_argument('--now', action='store_true',
                        help='собрать данные один раз и выйти')
    parser.add_argument('--time', default='19:00',
                        help='время ежедневного запуска (чч:мм)')
    args = parser.parse_args()

    if args.now:
        job()
    else:
        run_schedule(args.time)
