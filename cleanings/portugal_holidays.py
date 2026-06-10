"""Portuguese national public holidays for a calendar year."""

from __future__ import annotations

from datetime import date, timedelta


def _easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (Anonymous algorithm)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def portugal_national_holidays(year: int) -> dict[date, str]:
    """Return national holiday dates and names for the given year."""
    easter = _easter_sunday(year)
    fixed = (
        (1, 1, "Ano Novo"),
        (4, 25, "Dia da Liberdade"),
        (5, 1, "Dia do Trabalhador"),
        (6, 10, "Dia de Portugal"),
        (8, 15, "Assunção de Nossa Senhora"),
        (10, 5, "Implantação da República"),
        (11, 1, "Todos os Santos"),
        (12, 1, "Restauração da Independência"),
        (12, 8, "Imaculada Conceição"),
        (12, 25, "Natal"),
    )
    holidays = {date(year, month, day): name for month, day, name in fixed}
    holidays[easter - timedelta(days=2)] = "Sexta-feira Santa"
    holidays[easter + timedelta(days=60)] = "Corpo de Deus"
    return holidays
