import re

from jaraco.financial import ofx


def test_date():
    assert re.fullmatch(r'\d{14}', ofx._date())
