1.12
====

* Refreshed project skeleton, now running tests under tox.

1.11
====

* Configured project for automatic releases and moved hosting to Github.

1.10
====

* Dropped support for Python 2.6.

1.9
===

* Removed dependency on ``jaraco.util``.

1.8
===

* Improved Python 3 support in more modules.

1.7
===

* Added support for updating the password in the keyring.

1.6
===

* YAML format is now the preferred format for accounts definitions. Support
  for JSON-formatted accounts definitions is still supported but deprecated.

1.5
===

* Added support for loading institutions from a YAML file (requires PyYAML
  to be installed).
* Added the ofx command list-institutions.

1.4
===

* Added support for launching downloaded ofx in money.
* Now validate downloaded OFX using ofxparse.
* Added --like parameter to download all to download a subset of accounts.

1.3
===

* Added routine for patching msmoney.exe for a bug revealed by Windows 8.

1.0
===

* `ofx` script now implements different commands. Where one called "ofx"
  before, now call "ofx query".
* Added new command "ofx download-all", which loads the accounts from a JSON
  file (~/Documents/Financial/accounts.json) and downloads transactions for
  the accounts listed in that file.
* Added command "record-document-hashes" for e-mailing record of the
  hashes of each document.

0.2
===

* Integrated OFX support based on scripts provided by Jeremy Jongsma. Includes
  ability to specify financial institutions as plugins and download OFX data
  via the command-line script `ofx`.
* Added keyring support, so credentials for financial institutions are stored
  securely within the Windows Vault.
* Added command to clean up temporary files that crash MS Money.

0.1
===

* Initial release with script for launching files in MS Money.
