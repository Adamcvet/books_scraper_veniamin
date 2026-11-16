"""Тесты для функций парсера из scraper.py.

Тесты обращаются к настоящему сайту books.toscrape.com,
поэтому для запуска нужен интернет.
"""

import pytest

from scraper import get_book_data, get_book_links, scrape_books, PAGE_URL

BOOK_URL = ('http://books.toscrape.com/catalogue/'
            'a-light-in-the-attic_1000/index.html')


@pytest.fixture(scope='module')
def book():
    """Данные одной книги, скачиваются один раз на все тесты модуля."""
    return get_book_data(BOOK_URL)


def test_book_is_dict_with_keys(book):
    expected_keys = {'title', 'category', 'price', 'rating', 'in_stock',
                     'description', 'product_information', 'url'}
    assert isinstance(book, dict)
    assert expected_keys <= set(book.keys())


def test_book_values(book):
    assert book['title'] == 'A Light in the Attic'
    assert book['category'] == 'Poetry'
    assert book['price'] == 51.77
    assert book['rating'] == 3
    assert book['product_information']['UPC'] == 'a897fe39b1053632'


def test_book_field_types(book):
    assert isinstance(book['price'], float)
    assert 1 <= book['rating'] <= 5
    assert book['in_stock'] >= 0
    assert len(book['description']) > 0


def test_page_has_20_links():
    links = get_book_links(PAGE_URL.format(1))
    assert len(links) == 20
    assert all(link.startswith('http://books.toscrape.com/catalogue/')
               for link in links)
    assert BOOK_URL in links


def test_scrape_one_page():
    books = scrape_books(n_pages=1)
    assert isinstance(books, list)
    assert len(books) == 20
    assert books[0]['title'] == 'A Light in the Attic'


def test_save_to_file(tmp_path):
    path = tmp_path / 'books.txt'
    scrape_books(is_save=True, n_pages=1, filename=str(path))
    lines = path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 20
