# Cursor Tasks Manifest for chart-fights

This is the canonical inventory of exactly 8 tasks. All other files must reference this instead of listing tasks inline.

| id | filename | area | role |
|----|----------|------|------|
| 001 | task-001-anti-cheat-normalization.md | anti-cheat | determinism, normalization verification |
| 002 | task-002-time-and-tempo.md | time/tempo | core |
| 003 | task-003-resources-and-sabotage.md | resources/sabotage | core |
| 004 | task-004-orders-and-core-loop.md | orders | core |
| 005 | task-005-realtime-backend.md | realtime backend | core |
| 006 | task-006-data-pipeline.md | data | foundational primary |
| 007 | task-007-frontend-streaming.md | frontend | core |
| 008 | task-008-voice-integration.md | voice | core |

## Notes
- Use this manifest for any task inventory.
- All tasks are self-contained in their .md files.
- Refer to docs/design/ for specs.
- History note: task-001 was previously associated with data-pipeline naming; separated for clarity (anti-cheat/normalization focus). Primary data pipeline is task-006. Both are distinct and detailed per AC3.
