import textwrap
import types

import ofxparse

from jaraco.financial import paychex


def test_main(tmp_path, monkeypatch, capsys):
    security = types.SimpleNamespace(ticker='ABC', uniqueid='123456789', name='ABC')
    ofx = types.SimpleNamespace(security_list=[security])
    monkeypatch.setattr(ofxparse.OfxParser, 'parse', lambda file: ofx)
    monkeypatch.setattr(paychex, 'header', lambda ofx: ['<header>'])
    monkeypatch.setattr(paychex, 'footer', lambda ofx: ['<footer>'])
    ofx_file = tmp_path / 'download.ofx'
    ofx_file.write_text('', encoding='utf-8')
    csv_file = tmp_path / 'download.csv'
    csv_file.write_text(
        textwrap.dedent(
            """
            Date, Ticker, Transaction, Amount, Price, Shares
            01/02/2023, ABC, Purchase, 100.00, 10.00, 10.000
            01/03/2023, null, Bogus, 0, 0, 0
            """
        ).lstrip(),
        encoding='utf-8',
    )
    paychex.main([str(csv_file), str(ofx_file)])
    out = capsys.readouterr().out
    assert out.startswith('<header>\n')
    assert out.endswith('<footer>\n')
    assert '<DTTRADE>20230102</DTTRADE>' in out
    assert '<UNIQUEID>123456789</UNIQUEID>' in out
    assert 'Bogus' not in out
