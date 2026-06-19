# mike-harness-template.todo.md

**Bead:** mike-harness-template-59m
**JTBD:** Когда новый пользователь синкает харнесс из git и toolchain ещё не
доустановлен, хотим чтобы харнесс работал (graceful degradation) и сам
доустанавливался — прописать через скилы / harness-workflow.yaml / хуки.

## Critical chain

- [x] `harness-workflow.yaml` — SSOT (getting_started, toolchain, graceful_degradation, lifecycle); закрыта висячая ссылка bootstrap §getting_started
- [x] `bd prime` SessionStart guard `command -v bd` (no-op до установки)
- [x] аудит bd-зависимых хуков на fail-open (5/5 деградируют) + jsonl fallback
- [x] секция в скиле 0-governance-harness-portability
- [ ] фальсификация: bd вне PATH → gate не блокирует, bootstrap зелёный
- [ ] regen checksum + verify
- [ ] land → origin/main
