import datetime

from jaraco.financial import ledger


def test_transaction_default_date():
    before = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    txn = ledger.Transaction(payee='someone')
    assert txn.date.tzinfo is None
    assert before <= txn.date
