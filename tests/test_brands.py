"""Тесты нормализации брендов."""
import pytest

from app.services.brands import normalize_brand


@pytest.mark.parametrize("raw,expected", [
    ("ЛУКОЙЛ", "Лукойл"),
    ("lukoil", "Лукойл"),
    ('ООО "Газпромнефть"', "Газпромнефть"),
    ("газпром нефть", "Газпромнефть"),
    ('ООО ТД "Татнефть"', "Татнефть"),  # двойная юр.форма срезается
    ("ОКА-ПРОПАН", "ОКА-ПРОПАН"),
    ("ока пропан", "ОКА-ПРОПАН"),
])
def test_known_brands(raw, expected):
    assert normalize_brand(raw) == expected


def test_none_and_empty():
    assert normalize_brand(None) is None
    assert normalize_brand("") is None
    # из одной юр.формы ничего не остаётся -> возвращаем исходник, не пустоту
    assert normalize_brand("ООО") == "ООО"


def test_unknown_brand_cleaned():
    """Неизвестный бренд: срезаем юр.форму и кавычки, оставляем имя."""
    assert normalize_brand('ООО "Ромашка"') == "Ромашка"


@pytest.mark.parametrize("raw,expected", [
    ("Оптима-Сервис", "Оптима-Сервис"),  # не схлопывать в «Опти»
    ("ИТКОЛ", "ИТКОЛ"),                    # не схлопывать в «ИТК»
])
def test_no_substring_false_positive(raw, expected):
    """Короткий алиас не должен матчиться внутри чужого слова."""
    assert normalize_brand(raw) == expected


def test_no_empty_string_returned():
    """Никогда не возвращаем пустую строку (ломает UI)."""
    for raw in ['""', "ООО ", "  ", 'АО ""']:
        result = normalize_brand(raw)
        assert result is None or result.strip() != ""
