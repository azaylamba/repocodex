## ADDED Requirements

### Requirement: Coding skill commits the reverse index beside metrics

The coding-agent skill, including the copy shipped inside the Agent Plugins tree, SHALL tell the agent that an accepted write or reanchor regenerates the reverse index outside `.context/` and that the same commit MUST include `.repocodex/reverse-index.md` and, when shards exist, the matching files under `.repocodex/reverse-index/`. Instructing the agent to commit `.context/` alone SHALL NOT be sufficient.

#### Scenario: Skill names the reverse-index commit path

- **GIVEN** the installed coding-agent skill text
- **WHEN** it describes what to stage after writing or reanchoring memory
- **THEN** it names `.repocodex/reverse-index.md` (and shard files under `.repocodex/reverse-index/` when applicable)
- **AND** it does not imply that committing `.context/` alone includes the reverse index
