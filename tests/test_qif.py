import sys

from jaraco.financial import qif


def test_fix_dates_cmd(tmp_path, monkeypatch):
    target = tmp_path / 'paypal.qif'
    target.write_text('!Type:Bank\nD01/31/2023\nT-10.00\n^\n', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['fix-dates', str(target)])
    qif.fix_dates_cmd()
    assert target.read_text(encoding='utf-8') == '!Type:Bank\nD31-01-2023\nT-10.00\n^\n'
