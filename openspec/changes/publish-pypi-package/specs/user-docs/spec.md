## REMOVED Requirements

### Requirement: Install docs do not assume PyPI

**Reason**: The PyPI project `repocodex` is this change. Telling first-time visitors to install from git only would contradict the published package.

**Migration**: Replaced by “Install docs present PyPI as the install path”. Git-tag and editable clone remain documented fallbacks.

## ADDED Requirements

### Requirement: Install docs present PyPI as the install path

`README.md` and `docs/install.md` SHALL tell a first-time visitor to install from PyPI with `pip install "repocodex==0.0.1"` (and `pip install "repocodex[mcp]==0.0.1"` for the optional extra). They MAY also document git-tag or local editable install as a fallback. They SHALL state that the first public release is experimental (`0.0.1`). They SHALL NOT present git-tag install as the only path.

#### Scenario: README install uses PyPI

- **GIVEN** the project README
- **WHEN** a first-time reader follows the install snippet
- **THEN** the primary command installs `repocodex==0.0.1` from PyPI
- **AND** they can reach `repocodex context` / `repocodex validate --diff` after that install or from a clone

#### Scenario: Install doc matches the shipped Action

- **GIVEN** `docs/install.md`
- **WHEN** it describes how CI gets the engine
- **THEN** it describes PyPI install of `repocodex==` matching `engine_version`
- **AND** it does not say the Action installs from `git+https://github.com/azaylamba/repocodex.git`

## MODIFIED Requirements

### Requirement: Install docs include optional MCP extra

`docs/install.md` SHALL document installing the optional `mcp` extra (`pip install "repocodex[mcp]==0.0.1"` or `pip install -e ".[mcp]"`) and then `repocodex install --mcp` as a working setup step for hosts that speak MCP over stdio. That step SHALL remain optional. The README SHALL remain the front door and SHALL NOT require MCP to complete the first install.

#### Scenario: Maintainer can wire MCP from install.md

- **GIVEN** `docs/install.md`
- **WHEN** a maintainer wants Cursor (or another stdio host) to call RepoCodex tools
- **THEN** they are instructed to install the `mcp` extra from PyPI (or an editable clone) and run `repocodex install --mcp`
- **AND** they can still complete CLI, hook, and Action setup without that step

#### Scenario: README stays the front door

- **GIVEN** the project README
- **WHEN** a first-time reader follows the install snippet
- **THEN** they can install from PyPI or a clone and run `repocodex install`, `context`, and `validate --diff`
- **AND** they are not required to install MCP to finish that path
