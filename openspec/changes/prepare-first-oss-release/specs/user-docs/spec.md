## ADDED Requirements

### Requirement: Install docs do not assume PyPI

`README.md` and `docs/install.md` SHALL tell a first-time visitor how to install from the public git tag on `azaylamba/repocodex` (or an equivalent local editable install). They SHALL NOT present `pip install repocodex` from PyPI as the install path until a later change adds a published package. They SHALL state that the first public release is experimental (`0.0.1`).

#### Scenario: README install works without PyPI

- **GIVEN** the project README
- **WHEN** a first-time reader follows the install snippet
- **THEN** the commands do not require a PyPI project named `repocodex`
- **AND** they can reach `repocodex context` / `repocodex validate --diff` after install from git or from a clone

#### Scenario: Install doc matches the shipped Action

- **GIVEN** `docs/install.md`
- **WHEN** it describes how CI gets the engine
- **THEN** it describes git-tag install matching `engine_version`
- **AND** it does not say the Action runs `pip install repocodex==` against PyPI

### Requirement: README names the author without becoming a bio

`README.md` SHALL include a short author byline that names Ajay Lamba and links the GitHub user or this repository, while remaining the front door (purpose, benefit, install, three commands, links to `docs/`). It SHALL NOT add a long personal bio or duplicate architecture.

#### Scenario: Byline is present and README stays short

- **GIVEN** the project README
- **WHEN** a first-time reader opens it
- **THEN** they can see that Ajay Lamba created the project
- **AND** they can still state purpose and benefit in one sentence
- **AND** they are still pointed at named docs for how it works, memory, agents, and install
