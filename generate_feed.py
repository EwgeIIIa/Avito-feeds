"""
generate_feed.py
Скрипт автогенерации фида для Авито Автозагрузки.

Логика:
1. Читает исходные данные объявлений из source_data.json (это вы редактируете руками —
   тексты, базовые цены, список городов и т.д. Это ваш "источник правды").
2. Применяет автоматические изменения при каждом запуске:
   - обновляет дату "актуально на" -> сигнал "живое" объявление
   - слегка колеблет цену в заданном диапазоне (чтобы цена не была "мёртвой")
   - выбирает следующий по очереди вариант описания (ротация текста)
3. Сохраняет итог в BaronNeon_feed.xlsx — именно этот файл лежит в репозитории
   и именно на него смотрит Авито через raw-ссылку.

Запускается вручную (python generate_feed.py) или автоматически через
GitHub Actions (см. .github/workflows/update-feed.yml).
"""

import json
import random
from datetime import datetime
from pathlib import Path

import pandas as pd

SOURCE_FILE = Path("source_data.json")
OUTPUT_FILE = Path("BaronNeon_feed.xlsx")  # имя должно совпадать с тем, что уже загружено на GitHub!


def load_source() -> list[dict]:
    """Загружаем исходные данные по объявлениям."""
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_description(variants: list[str], run_index: int) -> str:
    """Ротация текста: берём следующий вариант описания по кругу."""
    if not variants:
        return ""
    return variants[run_index % len(variants)]


def jitter_price(base_price: int, spread_percent: float = 3.0) -> int:
    """Небольшое случайное колебание цены в пределах +-spread_percent%."""
    delta = base_price * (spread_percent / 100)
    new_price = base_price + random.uniform(-delta, delta)
    # округляем до кратного 10, чтобы цена выглядела естественно
    return int(round(new_price / 10) * 10)


def build_feed_rows(items: list[dict]) -> list[dict]:
    """Строим итоговые строки фида в формате, который понимает Авито Автозагрузка.

    ВАЖНО: названия колонок ниже — примерные (стандартный набор для услуг/товаров).
    Уточните точный список обязательных колонок в разделе Авито:
    Личный кабинет -> Автозагрузка -> Инструкция / Скачать шаблон.
    Переименуйте ключи в этом словаре под требования вашего шаблона.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    run_index = int(datetime.now().timestamp()) // 86400  # меняется раз в сутки

    rows = []
    for item in items:
        rows.append(
            {
                "Id": item["id"],
                "Title": item["title"],
                "Description": pick_description(item.get("description_variants", []), run_index),
                "Price": jitter_price(item["base_price"], item.get("price_spread_percent", 3)),
                "Category": item["category"],
                "Address": item["address"],
                "Images": ", ".join(item.get("images", [])),
                "AdType": item.get("ad_type", "Услуга"),
                "DateUpdated": today,
            }
        )
    return rows


def main():
    items = load_source()
    rows = build_feed_rows(items)
    df = pd.DataFrame(rows)
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Готово: {OUTPUT_FILE} обновлён, строк: {len(rows)}")


if __name__ == "__main__":
    main()
