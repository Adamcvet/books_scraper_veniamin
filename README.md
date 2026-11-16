# Books Scraper

Домашнее задание 3 по курсу Python: парсинг, Git и тестирование.

## Цель

Автоматически собирать данные о всех книгах с сайта
[Books to Scrape](http://books.toscrape.com): название, жанр, цену, рейтинг,
количество в наличии, описание и таблицу Product Information.
Сбор запускается каждый день в 19:00, результат сохраняется в
`artifacts/books_data.txt`.

## Структура проекта

```
books_scraper/
├── artifacts/
│   └── books_data.txt        # результат парсинга (1000 книг, по одной на строку в JSON)
├── notebooks/
│   └── HW_03_python_ds.ipynb
├── tests/
│   └── test_scraper.py       # тесты на pytest
├── scraper.py                # код парсера и планировщика
├── pytest.ini
├── requirements.txt
└── README.md
```

## Установка

```bash
git clone <ссылка на репозиторий>
cd books_scraper
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск

Однократный сбор данных:

```bash
python scraper.py --now
```

Ежедневный запуск по расписанию (по умолчанию в 19:00, скрипт работает, пока его не остановить через Ctrl+C):

```bash
python scraper.py
python scraper.py --time 08:30   # другое время
```

Тесты (нужен интернет, т.к. они обращаются к сайту):

```bash
pytest -v
```

## Формат данных

Каждая строка `books_data.txt` - это JSON-объект с одной книгой:

```json
{"title": "A Light in the Attic", "category": "Poetry", "price": 51.77, "rating": 3, "in_stock": 22, "description": "...", "product_information": {"UPC": "a897fe39b1053632", "...": "..."}, "url": "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"}
```

Прочитать файл обратно можно так:

```python
import json

with open('artifacts/books_data.txt', encoding='utf-8') as f:
    books = [json.loads(line) for line in f]
```

## Используемые библиотеки

- `requests` - загрузка страниц
- `beautifulsoup4` - разбор HTML
- `schedule` - запуск по расписанию
- `pytest` - тесты
