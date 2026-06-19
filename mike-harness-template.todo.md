# mike-harness-template.todo.md

**Bead:** mike-harness-template-uy8
**JTBD:** Когда участник клонирует харнесс из git, хотим чтобы установка всего
(beads/Dolt/python-deps) и getting-started запускались автоматически, без ручных шагов.

## Critical chain

- [x] RCA: почему toolchain не ставился по умолчанию → 5 Whys (`docs/why-harness-not-installed-5-whys.md`)
- [x] `scripts/setup/install_all.sh` — idempotent установщик всего toolchain
- [x] `scripts/harness_bootstrap.py` — авто-запуск установщика на SessionStart (marker-guarded) + шаг `toolchain`
- [x] `docs/GETTING_STARTED.md` — что Мише знать про харнесс, скилы, агентов, как ставить/запускать задачи
- [x] `requirements.txt` — добавить networkx (граф зависимостей)
- [x] README/CHANGELOG обновить
- [ ] regen checksum-манифест (новые/изменённые harness-файлы)
- [ ] land → origin/main
