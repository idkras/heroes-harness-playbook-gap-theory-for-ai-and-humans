# Hook JTBD registry — что каждый хук делает + покрыт ли eval

**GENERATED — не редактировать руками.** SSOT: `gen_hook_jtbd_registry.py` (этот же каталог). Перегенерировать: `python3 gen_hook_jtbd_registry.py --write`.

**Назначение (JTBD):** когда хук в системе git-sync/governance меняется или удаляется — видим его назначение и eval-покрытие, чтобы НЕ потерять JTBD хука и механически ловить регрессию «хуже не стало» (`--check` в lefthook pre-push).

**Легенда статуса:**

- 🟢 — wired + есть eval-фикстура (регрессия ловится)
- 🟡 — wired, eval осознанно не нужен (waiver с причиной)
- 🔴 — wired, БЕЗ eval и БЕЗ waiver → регрессия НЕ ловится (долг R2)
- ⚪ — deprecated / кандидат на удаление (см. note)

**Сводка:** wired=52 · 🟢 20 · 🟡 3 · 🔴 29 · ⚪ 0

| Статус | Хук | Событие | JTBD (назначение) | Eval | Note |
|---|---|---|---|---|---|
| 🔴 | `<teammate>_pr_gate` | PreToolUse | <teammate> PR gate — Claude Code PreToolUse hook for Bash matcher. | — |  |
| 🟢 | `auto_commit_on_stop` | Stop | Auto-commit-on-Stop — Claude Code Stop hook. | smoke |  |
| 🔴 | `branch_closure_diff_check` | PreToolUse | branch_closure_diff_check — Claude Code PreToolUse Bash matcher. | — |  |
| 🟢 | `branch_name_bead_ref_check` | PreToolUse | branch_name_bead_ref_check.py — PreToolUse Bash hook: проверка что новые ветки | smoke |  |
| 🔴 | `client_domain_registry_gate` | PreToolUse | Client domain registry gate — Claude Code PreToolUse hook. | — |  |
| 🔴 | `coherent_narrative_check` | Stop | Coherent narrative check — Claude Code Stop hook. | — |  |
| 🔴 | `credential_key_alias_search` | PreToolUse | Credential key-alias false-negative guard — Claude Code PreToolUse(Bash) hook. | — |  |
| 🟢 | `destructive_op_full_ban` | PreToolUse | PreToolUse hook — full ban on destructive git/fs operations on shared/local resources. | smoke |  |
| 🟢 | `detachable_skill_packaging_gate` | PreToolUse | PreToolUse gate: keep skill logic out of top-level scripts/. | smoke |  |
| 🔴 | `expected_output_announce_check` | PreToolUse | Expected output announce check — Claude Code PreToolUse hook. | — |  |
| 🟢 | `first_substantial_write_branch_bead_gate` | PreToolUse | first_substantial_write_branch_bead_gate — PreToolUse Write\|Edit hook. | smoke |  |
| 🟢 | `gap_count_delivery` | Stop | Stop-hook: считает ЧИСЛО гепов (разрывов) в последнем выводе агента и выводит счётчик. | smoke |  |
| 🔴 | `gap_symmetry_table_check` | Stop | Gap-symmetry table-language check — Claude Code Stop hook. | — |  |
| 🔴 | `git_dirty_count_gate` | PreToolUse | Git dirty count gate — Claude Code PreToolUse hook. | — |  |
| 🟢 | `git_worktree_completeness_gate` | PreToolUse | git_worktree_completeness_gate — Claude Code PreToolUse Bash matcher. | smoke |  |
| 🟢 | `graphql_operation_schema_match` | PreToolUse | PreToolUse Write/Edit hook: enforce schema citation for GraphQL operations. | unit |  |
| 🔴 | `inventory_response_format_check` | Stop | inventory-response-format-check — Stop-event hook (RCA 2026-06-01). | — |  |
| 🔴 | `legacy_path_block_check` | PreToolUse | Legacy path block check — Claude Code PreToolUse hook. | — |  |
| 🔴 | `mcp_server_smoke_check` | PostToolUse | MCP server smoke check — Claude Code PostToolUse hook. | — |  |
| 🟢 | `merged_claim_verification` | Stop | Stop hook — Pillar B (Standard 0.2 §3): block "merged / in origin/main / | smoke |  |
| 🔴 | `offer_message_review_check` | PostToolUse | Offer & Telegram Message Review check — Claude Code PostToolUse hook. | — |  |
| 🟢 | `oneof_input_variant_exhaustion` | PreToolUse | PreToolUse Write/Edit hook: enforce @oneOf variant rationale for GraphQL inputs. | unit |  |
| 🟢 | `orchestrator_stage_tracker_check` | Stop | orchestrator_stage_tracker_check — Stop event hook. | smoke |  |
| 🟢 | `owner_effort_scale_check` | Stop | Owner effort scale check — Claude Code Stop hook. | smoke |  |
| 🔴 | `pending_owner_claim_verification` | PreToolUse | Pending-owner claim verification — Claude Code PreToolUse hook. | — |  |
| 🔴 | `pre_git_clean_parallel_check` | PreToolUse | PreToolUse hook — block `git clean -fd <path>` if path matches parallel-session work. | — |  |
| 🔴 | `pre_push_deletion_guard` | PreToolUse, lefthook(git) | pre_push_deletion_guard.py — universal mass-deletion catastrophe prevention. | — |  |
| 🟢 | `pre_push_submodule_ref_on_origin_check` | lefthook(git) | pre-push guard: block a push that bumps a submodule pointer to a sha that | smoke |  |
| 🔴 | `project_launch_todo_check` | PostToolUse | PostToolUse hook for `bd create --type epic` (or `--type=epic`). | — |  |
| 🔴 | `project_structure_guardian_check` | PreToolUse | project-structure-guardian-check — PreToolUse Read hook (RCA 2026-06-01 part 2). | — |  |
| 🟢 | `raw_data_rows_in_chat_check` | Stop | Raw-data-rows-in-chat check — Claude Code Stop hook. | unit |  |
| 🔴 | `reasoning_log_audit` | PostToolUse | PostToolUse audit hook for reasoning-log §H enforcement. | — |  |
| 🟡 | `reasoning_log_stop` | Stop | Stop hook: append session-end row to reasoning log. | waiver | append-only лог-строка на Stop, без условной логики блокировки |
| 🟢 | `reusable_script_belongs_in_skill_gate` | PreToolUse | PreToolUse gate: reusable-скрипт должен жить В СКИЛЕ, не валяться в client-папке. | smoke |  |
| 🔴 | `rickai_kb_guardian_check` | PostToolUse | Rickai KB Guardian check — Claude Code PostToolUse hook. | — |  |
| 🔴 | `rickai_pipeline_output_path_gate` | PreToolUse | rickai_pipeline_output_path_gate — PreToolUse Bash hook. | — |  |
| 🟢 | `secret_pattern_in_draft_files` | PreToolUse | Secret-pattern-in-draft-files hook — Claude Code PreToolUse for Write/Edit/NotebookEdit. | smoke |  |
| 🔴 | `session_end_auto_push` | SessionEnd | Session-end auto-push — the MISSING leg that makes WIP reach the team. | — |  |
| 🟡 | `session_isolation_guard` | SessionStart | Session isolation guard — Claude Code SessionStart hook. | waiver | SessionStart advisory-only, печатает баннер, не блокирует — нечего фальсифицировать |
| 🟢 | `skill_creation_review_gate` | PreToolUse | Skill-creation review gate — Claude Code PreToolUse hook. | smoke |  |
| 🔴 | `skill_diagnostic_recurrence_invalidator` | PostToolUse | Skill diagnostic recurrence invalidator — PostToolUse hook on ai.incidents.md. | — |  |
| 🟡 | `skill_path_scope_activate` | PostToolUse | PostToolUse hook — path-scoped skill activation (helpline `paths:` pattern). | waiver | PostToolUse path-scoped surface, без exit-2 ветки |
| 🔴 | `source_read_before_4xx_diagnosis` | PreToolUse | Source-read-before-4xx-diagnosis — Claude Code PreToolUse hook. | — |  |
| 🔴 | `standards_creation_routing_gate` | PreToolUse | Standards-creation routing gate — Claude Code PreToolUse hook. | — |  |
| 🔴 | `stop_event_claim_verification` | Stop | stop_event_claim_verification — Claude Code Stop event hook. | — |  |
| 🔴 | `substantial_task_orchestrator_trigger` | PostToolUse | Substantial task → orchestrator/manager-audit trigger — PostToolUse counter hook. | — |  |
| 🔴 | `untracked_critical_files_gate` | PreToolUse | Untracked critical files gate — Claude Code PreToolUse hook (RCA 2026-05-15). | — |  |
| 🟢 | `userprompt_branch_bead_nudge` | UserPromptSubmit | userprompt_branch_bead_nudge — Claude Code UserPromptSubmit hook. | smoke |  |
| 🔴 | `viral_tg_prepublish_gate` | PreToolUse | Viral Telegram pre-publish gate — PreToolUse hook. | — |  |
| 🟢 | `work_time_state_drift_guard` | PreToolUse | work_time_state_drift_guard — Claude Code PreToolUse Write\|Edit\|Bash hook. | smoke |  |

## Как читать «хуже не стало»

Каждый 🟢 хук имеет фикстуру в `scripts/test_hooks_smoke.py` или `.claude/hooks/tests/test_*.py`. Перед sync/push: `python3 scripts/test_hooks_smoke.py` (см. lefthook pre-push) — если хоть одна фикстура красная, push прерывается. `gen_hook_jtbd_registry.py --check` дополнительно падает, если появился новый wired-хук без eval и без waiver (новый 🔴), чтобы покрытие не деградировало молча.
