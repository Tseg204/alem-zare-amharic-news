"""Ethiopian calendar date for an edition — computed, so the AI never has to guess it.

Usage:
    python3 etdate.py 2026-11-10
prints JSON with the three date fields stories.json needs:
    {"date_gc": "10 Nov 2026",
     "date_et": "ኅዳር 1, 2019 ዓ.ም",
     "date_et_spoken": "ኅዳር አንድ፣ ሁለት ሺህ አሥራ ዘጠኝ ዓመተ ምሕረት"}
`date_et_spoken` is the form the narration reads (cover_speech): numbers in Amharic words.
validate.py uses date_et() to check that stories.json has the right Ethiopian date.
"""
import json, sys
from datetime import date

MONTHS = ["መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ", "ጥር", "የካቲት", "መጋቢት",
          "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ"]
ONES = ["", "አንድ", "ሁለት", "ሦስት", "አራት", "አምስት", "ስድስት", "ሰባት", "ስምንት", "ዘጠኝ"]
TENS = ["", "አሥር", "ሃያ", "ሠላሳ", "አርባ", "ሃምሳ", "ስልሳ", "ሰባ", "ሰማንያ", "ዘጠና"]
ET_EPOCH = 2796             # fixed day number (Rata Die, = date.toordinal()) of 1 Meskerem, year 1


def _fixed(y, m, d):
    return ET_EPOCH - 1 + 365 * (y - 1) + y // 4 + 30 * (m - 1) + d


def to_ethiopian(d: date):
    """Gregorian date → (year, month 1–13, day). Formula from Reingold & Dershowitz,
    Calendrical Calculations; the extra day (Pagume 6) comes at the end of years where year % 4 == 3."""
    rd = d.toordinal()
    y = (4 * (rd - ET_EPOCH) + 1463) // 1461
    m = (rd - _fixed(y, 1, 1)) // 30 + 1
    return y, m, rd + 1 - _fixed(y, m, 1)


def words(n: int) -> str:
    """0 < n < 10000 in Amharic words (enough for days and years)."""
    parts = []
    if n >= 1000:
        parts.append(f"{ONES[n // 1000]} ሺህ")
        n %= 1000
    if n >= 100:
        parts.append("መቶ" if n // 100 == 1 else f"{ONES[n // 100]} መቶ")
        n %= 100
    if n >= 10:
        t, o = divmod(n, 10)
        parts.append(f"{TENS[t]}" if o == 0 else (f"አሥራ {ONES[o]}" if t == 1 else f"{TENS[t]} {ONES[o]}"))
    elif n:
        parts.append(ONES[n])
    return " ".join(parts)


def date_et(d: date) -> str:
    y, m, day = to_ethiopian(d)
    return f"{MONTHS[m - 1]} {day}, {y} ዓ.ም"


def fields(d: date) -> dict:
    y, m, day = to_ethiopian(d)
    return {
        "date_gc": f"{d.day} {d.strftime('%b')} {d.year}",
        "date_et": date_et(d),
        "date_et_spoken": f"{MONTHS[m - 1]} {words(day)}፣ {words(y)} ዓመተ ምሕረት",
    }


if __name__ == "__main__":
    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(json.dumps(fields(d), ensure_ascii=False, indent=1))
