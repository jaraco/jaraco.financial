from jaraco.financial.qif import InvestmentTransaction


def test_investment_transaction_qif_fields():
    transaction = InvestmentTransaction()
    vars(transaction).update(
        type='Invst',
        qif_date='10/09/2026',
        amount='123.45',
        inv_type='Buy',
        fund='Example Fund',
        price='12.345',
        quantity='10',
    )
    assert transaction.qif_str().splitlines() == [
        '!Type:Invst',
        'D10/09/2026',
        'T123.45',
        'NBuy',
        'YExample Fund',
        'I12.345',
        'Q10',
        '^',
    ]
