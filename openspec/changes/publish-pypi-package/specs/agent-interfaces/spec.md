## REMOVED Requirements

### Requirement: Shipped Action installs the pinned engine from git

**Reason**: Git-tag install was the first-public-release floor until a PyPI project existed. The Action must resolve the same pin from PyPI so consuming CI does not clone this repository.

**Migration**: Replaced by “Shipped Action installs the pinned engine from PyPI”. Re-run `repocodex install` in consuming repos to rewrite the workflow.

## ADDED Requirements

### Requirement: Shipped Action installs the pinned engine from PyPI

The GitHub Action that `repocodex install` writes SHALL install the engine with `pip install repocodex==<engine_version>` from PyPI (or an equivalent pin that matches `engine_version`). It SHALL still run `repocodex validate --diff --check` as the required job. It SHALL NOT install from `git+https://github.com/azaylamba/repocodex.git@v<engine_version>` as the primary source.

#### Scenario: Required job installs the pin from PyPI

- **GIVEN** a repository where `repocodex install` has written `.github/workflows/repocodex.yml` and `.repocodex.toml` with `engine_version = "0.0.1"`
- **WHEN** the required check job installs the engine
- **THEN** the install source is PyPI package `repocodex` version `0.0.1`
- **AND** the job still invokes `repocodex validate` with `--check`
