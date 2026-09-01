## REMOVED Requirements

### Requirement: Install and consuming CI work without PyPI

**Reason**: The deferred PyPI project is this change. Git-tag install was the first-public-release floor, not the long-term pin source.

**Migration**: Replaced by “Install and consuming CI use the PyPI project”. Git tag `v<engine_version>` remains a documented fallback, not the Action install source.

## ADDED Requirements

### Requirement: Install and consuming CI use the PyPI project

Installing the engine for humans and for the shipped GitHub Action SHALL use the PyPI project `repocodex` at the version that matches `engine_version` (`pip install repocodex==<engine_version>`). The published version SHALL be `0.0.1`. Git-tag install MAY remain documented as a fallback. They SHALL NOT require cloning `azaylamba/repocodex` to run the pin-check Action.

#### Scenario: Action installs from PyPI at the pin

- **GIVEN** `.repocodex.toml` with `engine_version = "0.0.1"`
- **AND** PyPI project `repocodex` has version `0.0.1`
- **WHEN** the shipped required-check job installs the engine
- **THEN** it installs `repocodex==0.0.1` from PyPI
- **AND** it does not install from `git+https://github.com/azaylamba/repocodex.git`

### Requirement: PyPI 0.0.1 matches the git tag identity

The sdist and wheel uploaded as PyPI `repocodex` version `0.0.1` SHALL be built from the commit tagged `v0.0.1`. That version SHALL be a final PEP 440 release (`0.0.1`), not a pre-release (`0.0.1a1`, `0.1.0a1`, or `0.1.0b1`). `pyproject.toml` version, `ENGINE_VERSION`, the default `engine_version` written by `repocodex install`, and the Action fallback pin SHALL remain `0.0.1`.

#### Scenario: One identity across git and PyPI

- **GIVEN** git tag `v0.0.1` and PyPI version `0.0.1`
- **WHEN** a caller compares package version, `ENGINE_VERSION`, and the default install pin
- **THEN** all are the string `0.0.1`
- **AND** the PyPI version is not a PEP 440 pre-release

### Requirement: Engine repository can publish with Trusted Publishing

This repository SHALL have a GitHub Actions workflow that builds the sdist and wheel and publishes them to PyPI using Trusted Publishing (OIDC), without storing a PyPI API token in the repository. A TestPyPI dry-run SHALL succeed before the first production upload. Manual twine MAY be used only as a fallback to claim the project if OIDC is not yet registered.

#### Scenario: Tag-triggered publish does not use a stored token

- **GIVEN** this repository’s publish workflow
- **WHEN** a version tag is pushed
- **THEN** the job builds with the standard Python build frontend
- **AND** it publishes via Trusted Publishing rather than a committed API token
