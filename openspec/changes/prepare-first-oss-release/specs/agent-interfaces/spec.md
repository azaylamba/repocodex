## ADDED Requirements

### Requirement: Shipped Action installs the pinned engine from git

The GitHub Action that `repocodex install` writes SHALL install the engine from `git+https://github.com/azaylamba/repocodex.git@v<engine_version>` (or an equivalent git ref that matches the pin). It SHALL still run `repocodex validate --diff --check` as the required job. It SHALL NOT install by querying PyPI for `repocodex==<pin>` until a later change publishes that package.

#### Scenario: Required job does not hit PyPI

- **GIVEN** a repository where `repocodex install` has written `.github/workflows/repocodex.yml` and `.repocodex.toml` with `engine_version = "0.0.1"`
- **WHEN** the required check job installs the engine
- **THEN** the install source is the `v0.0.1` git tag on `azaylamba/repocodex`
- **AND** the job still invokes `repocodex validate` with `--check`

### Requirement: First public release does not advertise a working MCP server

`repocodex install --mcp` SHALL NOT report MCP as successfully registered while the `mcp` CLI command cannot start a server. User-facing docs for this release SHALL NOT list MCP registration as a working setup step. Skills, CLI, hook, and the pin-check Action SHALL remain the supported surfaces.

#### Scenario: install --mcp does not claim a working server

- **GIVEN** a repository and a `repocodex` build whose `mcp` command cannot start
- **WHEN** `repocodex install --mcp` runs
- **THEN** the payload does not list MCP as an installed working surface
- **AND** `ok` is not true solely because an `mcp.json` was copied

#### Scenario: Skills-only setup is the documented path

- **GIVEN** `docs/install.md` after this change
- **WHEN** a maintainer wires a repo
- **THEN** they are instructed to install CLI, hook, Action, and skills
- **AND** they are not instructed that `repocodex install --mcp` will start a server

## MODIFIED Requirements

### Requirement: Optional MCP wrapper

The system MAY provide an optional MCP server exposing `get_context`, `get_impact`, `read_concept`, `write_memory`, `validate_diff`, and `reconcile_memory` as thin wrappers over the corresponding CLI commands, with identical verdicts. Until that server can be started with the documented extra, the first public release SHALL treat MCP as unavailable: it SHALL NOT document it as a working extra, and `repocodex install --mcp` SHALL NOT report success. A skills-only client SHALL still work. When a later change ships a starting server, MCP and CLI SHALL agree on verdicts including `engine_version`.

#### Scenario: MCP and CLI agree

- **GIVEN** a build in which the MCP server starts
- **AND** the same diff
- **WHEN** validation runs via the MCP tool and via the CLI
- **THEN** the verdicts are identical, including `engine_version`

#### Scenario: First public release without a starting server

- **GIVEN** a build in which the MCP server does not start
- **WHEN** a newcomer follows install docs
- **THEN** they can use CLI, skills, hook, and pin-check CI
- **AND** they are not told that MCP is a working extra
