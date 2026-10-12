from jaraco.financial.lifo import DictWriter, write


def test_output_file_can_be_written(tmp_path):
    destination = tmp_path / 'allocations.csv'
    with write(destination) as stream:
        output = DictWriter(stream)
        output.fieldnames = ['Lot', 'Basis']
        output.writeheader()
        output.writerow({'Lot': 1, 'Basis': '12.50'})
    assert destination.read_text().splitlines() == ['Lot,Basis', '1,12.50']
