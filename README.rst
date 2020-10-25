.. image:: https://img.shields.io/pypi/v/jaraco.financial.svg
   :target: `PyPI link`_

.. image:: https://img.shields.io/pypi/pyversions/jaraco.financial.svg
   :target: `PyPI link`_

.. _PyPI link: https://pypi.org/project/jaraco.financial

.. image:: https://github.com/jaraco/jaraco.financial/workflows/Automated%20Tests/badge.svg
   :target: https://github.com/jaraco/jaraco.financial/actions?query=workflow%3A%22Automated+Tests%22
   :alt: Automated Tests

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: Black

.. image:: https://readthedocs.org/projects/jaracofinancial/badge/?version=latest
   :target: https://jaracofinancial.readthedocs.io/en/latest/?badge=latest

``jaraco.financial`` implements tools for financial management, particularly
around Open Financial Exchange and Microsoft Money. These scripts help
facilitate the continued use of Money using the free, sunset release, by
enabling mechanical downloads of OFX data from institutions that support OFX.

Getting Started
---------------

The primary use of this package is the `ofx` command. After installing, run
`ofx --help` for usage. Before using the project, you will want to supply
institution and account information. See below for details on defining these
input files.

This project is still a work in progress, but if you think you might find
it useful, don't hesitate to contact the author for help.

Planned Changes
---------------

The author plans to add some of the following features:

* Integrate some of the most common institutions.

Accounts File
-------------

The "ofx download-all" command of `jaraco.financial` will retrieve the
OFX transactions in a batch for a group of accounts defined in a YAML file.
Currently, that file must be located in ~/Documents/Financial/accounts.yaml.
The file should be a list of objects,
each with `institution` and `account` attributes. It should also have a
`type` property of "checking", "savings", "creditline", or other appropriate
OFX type. The institution must match exactly an institution as defined below.
Here is an example accounts.yaml::

    - institution: Bank of America
      account: "12345679"
      type: savings

    - institution: Wells Fargo
      account: "872634126"
      type: moneymrkt

    - institution: Chase (credit card)
      account: "4000111122223333"
      username: myusername

The `username` attribute must be included if the username of the local user
(running the ofx command) differs from the account name on the account.

Institutions Definition
-----------------------

Institution definitions can be provided in a YAML format in the file
``~/Documents/Financial/institutions.yaml``. The following is an example
definition for a credit card::

    Chase (credit card):
      caps:
       - SIGNON
       - CCSTMT
      fid: "10898"
      fiorg: B1
      url: https://ofx.chase.com

To check that your institutions are being loaded correctly, use the
``ofx list-institutions`` command.