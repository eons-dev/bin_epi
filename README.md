# eons Module Installer

![build](https://github.com/eons-dev/bin_emi/actions/workflows/python-package.yml/badge.svg)

EMI (or emi) is a package manager that uses the eons python library. The default repository is https://infrastructure.tech.


## Installation
`pip install emi`

## Usage

Emi should behave as expected: you can `install`, `update` and `remove` packages. Each package must have a valid install.json. Installation is platform agnostic, to a degree. Each package is responsible for maintaining its own cross-platform viability.

### Repository

Online repository settings can be specified with:
```
--repo-store (default = ./eons/)
--repo-url (default = https://api.infrastructure.tech/v1/package)
--repo-username
--repo-password
```

NOTE: you do not need to supply any repo settings to download packages from the public repository.
Because these creds are not pulled from environment variables and are visible on the command line, it is advisable to use app tokens with short expirations. This will be addressed in a future release.

For more info on the repo integration, see [the eons library](https://github.com/eons-dev/lib_eons#online-repository)
