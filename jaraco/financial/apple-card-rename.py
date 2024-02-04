import autocommand
import dateutil.parser
import path


def clean_name(orig):
    """
    >>> str(clean_name('Apple Card Transactions - November 2022.ofx'))
    '2022-11.ofx'
    >>> str(clean_name('root/Apple Card Transactions - July 2022.ofx'))
    'root/2022-07.ofx'
    """
    orig = path.Path(orig)
    leader, sep, date = orig.stem.partition(' - ')
    parsed = dateutil.parser.parse(date)
    return orig.with_stem(parsed.strftime('%Y-%m'))


def rename_all(dir):
    txn_files = list(dir.glob('Apple Card Transactions - *.ofx'))
    for file in txn_files:
        file.rename(clean_name(file))
    print("Renamed", len(txn_files), "files")


@autocommand.autocommand(__name__)
def run(root=path.Path()):
    rename_all(root)
