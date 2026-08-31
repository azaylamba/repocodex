## ADDED Requirements

### Requirement: MIT license is a file in the repository

The repository SHALL contain a root `LICENSE` file whose terms are MIT. Package metadata SHALL declare MIT and SHALL include that file in the built distribution.

#### Scenario: GitHub and the sdist can see the license

- **GIVEN** a clone of the repository
- **WHEN** a caller looks at the repo root and at package metadata
- **THEN** `LICENSE` exists
- **AND** metadata identifies MIT
- **AND** building an sdist includes `LICENSE`

### Requirement: First public version is experimental 0.0.1

The published engine identity SHALL be `0.0.1`: pyproject version, `ENGINE_VERSION`, the default `engine_version` written by `repocodex install`, and the fallback pin in the shipped Action SHALL all be that string. Docs SHALL describe the first public cut as experimental, not as a finished 1.0.

#### Scenario: Pin and running engine agree at 0.0.1

- **GIVEN** a fresh `repocodex install` with no existing `.repocodex.toml`
- **WHEN** the engine runs `validate`
- **THEN** output `engine_version` is `0.0.1`
- **AND** the written pin is `0.0.1`
- **AND** no user-facing doc calls the release `1.0.0`

### Requirement: Install and consuming CI work without PyPI

Installing the engine for humans and for the shipped GitHub Action SHALL use a git ref on `https://github.com/azaylamba/repocodex` that matches `engine_version` (tag `v<engine_version>`). They SHALL NOT require a PyPI project named `repocodex`.

#### Scenario: Action installs from the version tag

- **GIVEN** `.repocodex.toml` with `engine_version = "0.0.1"`
- **AND** git tag `v0.0.1` exists on `azaylamba/repocodex`
- **WHEN** the shipped required-check job installs the engine
- **THEN** it installs from that git tag
- **AND** it does not run `pip install repocodex==0.0.1` against PyPI

### Requirement: Engine repository has pytest CI

This repository SHALL have a GitHub Actions workflow that on pull request and on push to `main` installs Python 3.11+, ripgrep, the package with dev extras, and runs pytest. That workflow SHALL NOT treat a missing `.context/` bundle as a pin-check failure.

#### Scenario: A pull request runs engine tests

- **GIVEN** a pull request against `main`
- **WHEN** the engine CI workflow runs
- **THEN** pytest executes
- **AND** a missing OKF bundle does not fail the job

### Requirement: Security contact is the personal GitHub project

`SECURITY.md` SHALL tell reporters to use GitHub issues (or GitHub private vulnerability reporting) on `azaylamba/repocodex`. It SHALL name that repository as the home of the project.

#### Scenario: A reporter knows where to file

- **GIVEN** `SECURITY.md`
- **WHEN** someone wants to report a vulnerability
- **THEN** they are directed to GitHub on `azaylamba/repocodex`
- **AND** they are not told to email an unpublished personal address as the only path

### Requirement: Authorship is Ajay Kumar on the personal GitHub user

Package metadata and the README SHALL identify **Ajay Kumar** as the author and SHALL link `https://github.com/azaylamba/repocodex` as Homepage, Source, and Issues. The intended public GitHub home SHALL be that personal repository, not an organization and not a second GitHub username.

#### Scenario: A visitor can tell who built it

- **GIVEN** the README and `pyproject.toml`
- **WHEN** a first-time visitor opens them
- **THEN** they see the name Ajay Kumar
- **AND** they can follow a link to `github.com/azaylamba/repocodex`
- **AND** authors is not the placeholder name `RepoCodex`

#### Scenario: Namespace stays the personal account

- **GIVEN** this change
- **WHEN** in-repo URLs and install git remotes are written
- **THEN** they use `azaylamba/repocodex`
- **AND** they do not introduce a new GitHub organization or username as the project home
