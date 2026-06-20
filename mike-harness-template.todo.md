# mike-harness-template.todo.md

**Bead:** mike-harness-template-wqm
**JTBD:** Когда участник ведёт проекты в харнессе, хотим папку projects/ +
подключённые Beads/Dolt/Graphify, чтобы вся работа запускалась через них.

## Critical chain

- [x] `scripts/graphify.py` — публичный graphify (networkx): beads + harness-workflow.yaml → graphify-out/graph.json (+ --doctor/--check)
- [x] подключить graphify в `scripts/setup/install_all.sh` (build на установке) + `graphify-out/` в .gitignore
- [x] `harness-workflow.yaml` — graphify из optional/canonical-only → public required
- [x] `projects/` + `projects/README.md` (модель: каждый проект через beads→worktree→graphify); легитимизирован в манифесте (allowed_dirs, убран из owner_decision)
- [x] guardian зелёный: wiring✅ graph✅ branch/bead✅ tools✅
- [x] GETTING_STARTED — обновлён graphify + ссылка на projects/
- [ ] regen checksum + verify
- [ ] GitHub sync: git push + bd dolt push
- [ ] land → origin/main
