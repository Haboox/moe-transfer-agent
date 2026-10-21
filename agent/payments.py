"""Card checks for the MOCK payment window. Deterministic, no real payment provider.

Only synthetic test card numbers are accepted, so a real card can never be charged or stored:
  4242 4242 4242 4242   Visa        approved
  5555 5555 5555 4444   Mastercard  approved
  4000 0000 0000 0002   Visa        declined by the (mock) bank
  4000 0000 0000 9995   Visa        declined: insufficient funds
These are the public test numbers payment providers publish for testing; they cannot move money.

Security choices (shown in the demo and in docs/06_architecture.md):
  * the card number, expiry and CVV are checked here and dropped; only brand and last 4 digits are kept
  * nothing about the card is written to the audit log except brand, last 4 and the outcome
  * any other card number, even a valid looking one, is refused as "not a test card"
"""
from __future__ import annotations

import re
from datetime import date

APPROVED = {"4242424242424242": "Visa", "5555555555554444": "Mastercard"}
DECLINED = {"4000000000000002": "card_declined", "4000000000009995": "insufficient_funds"}


class CardError(Exception):
    """A payment the mock gateway refuses. args[0] is a code the UI shows in the customer's language."""

    @property
    def code(self) -> str:
        return self.args[0]


def digits(number: str) -> str:
    return re.sub(r"\D", "", number or "")


def luhn_ok(number: str) -> bool:
    d = digits(number)
    if not 12 <= len(d) <= 19:
        return False
    total = 0
    for i, ch in enumerate(reversed(d)):
        n = int(ch)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def card_brand(number: str) -> str:
    d = digits(number)
    if d.startswith("4"):
        return "Visa"
    if d[:2] in {"51", "52", "53", "54", "55"} or 2221 <= int(d[:4] or 0) <= 2720:
        return "Mastercard"
    return "Card"


def expiry_ok(expiry: str, today: date) -> bool:
    m = re.fullmatch(r"\s*(\d{1,2})\s*/\s*(\d{2}|\d{4})\s*", expiry or "")
    if not m:
        return False
    month, year = int(m.group(1)), int(m.group(2))
    year = year + 2000 if year < 100 else year
    if not 1 <= month <= 12:
        return False
    return (year, month) >= (today.year, today.month)


def check_card(card: dict, today: date) -> None:
    """Raises CardError with a code; returns None when the (test) card is approved."""
    number = digits(card.get("number", ""))
    if not (card.get("name") or "").strip():
        raise CardError("name_missing")
    if not luhn_ok(number):
        raise CardError("number_invalid")
    if not expiry_ok(card.get("expiry", ""), today):
        raise CardError("expiry_invalid")
    if not re.fullmatch(r"\d{3,4}", (card.get("cvv") or "").strip()):
        raise CardError("cvv_invalid")
    if number in DECLINED:
        raise CardError(DECLINED[number])
    if number not in APPROVED:
        raise CardError("not_test_card")
