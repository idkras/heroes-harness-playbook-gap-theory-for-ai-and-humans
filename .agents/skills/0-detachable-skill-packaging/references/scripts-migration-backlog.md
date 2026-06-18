# Skill-packaging inventory

Classification of `scripts/` files for migration into owning skills.
Canon: skill `0-detachable-skill-packaging`.

| script_path | category | owning_skill | referenced_by | recommended_action |
|---|---|---|---|---|
| `scripts/advising_clients_sweep.py` | skill-owned | 3-client-file-intake-from-telegram | 3-client-file-intake-from-telegram,4-rick-client-data-curator,7-rick-client-google-drive-locator | move into .agents/skills/3-client-file-intake-from-telegram/scripts/ + tests/ |
| `scripts/audit_rick_kb_templates.py` | skill-owned | 0-rickai-kb-guardian | 0-rickai-kb-guardian,4-rick-kb-guardian,rick-kb-guardian | move into .agents/skills/0-rickai-kb-guardian/scripts/ + tests/ |
| `scripts/backfill_canonical_gdrive.py` | skill-owned | 4-rick-client-data-curator | 4-rick-client-data-curator,7-rick-client-google-drive-locator,lisa-client-care-curator | move into .agents/skills/4-rick-client-data-curator/scripts/ + tests/ |
| `scripts/bcs_write_template_sheet.py` | skill-owned | cohort-delivery-manager | cohort-delivery-manager | move into .agents/skills/cohort-delivery-manager/scripts/ + tests/ |
| `scripts/check_windows_safe_filenames.py` | skill-owned | 5-sync-github-checklist | 5-sync-github-checklist,7-advising-roadmap-sync-local | move into .agents/skills/5-sync-github-checklist/scripts/ + tests/ |
| `scripts/<internal-component>/__init__.py` | skill-owned | 0-detachable-skill-packaging | 0-detachable-skill-packaging,<teammate>-code-review | move into .agents/skills/0-detachable-skill-packaging/scripts/ + tests/ |
| `scripts/<internal-component>/auth.py` | skill-owned | 1-auto-continue-unfinished | 1-auto-continue-unfinished,4-rickai-ga4-property-attach,4-source-code-dive-before-claim | move into .agents/skills/1-auto-continue-unfinished/scripts/ + tests/ |
| `scripts/<internal-component>/config.py` | skill-owned | 5-rick-ai-<internal-component>-workflow | 5-rick-ai-<internal-component>-workflow,<teammate>-code-review | move into .agents/skills/5-rick-ai-<internal-component>-workflow/scripts/ + tests/ |
| `scripts/<internal-component>/main.py` | skill-owned | 3-client-chat-delivery | 3-client-chat-delivery,5-rick-ai-<internal-component>-workflow,8-telegram-add-teammate | move into .agents/skills/3-client-chat-delivery/scripts/ + tests/ |
| `scripts/<internal-component>/__init__.py` | skill-owned | 0-detachable-skill-packaging | 0-detachable-skill-packaging,<teammate>-code-review | move into .agents/skills/0-detachable-skill-packaging/scripts/ + tests/ |
| `scripts/<internal-component>/adapters/__init__.py` | skill-owned | 0-detachable-skill-packaging | 0-detachable-skill-packaging,<teammate>-code-review | move into .agents/skills/0-detachable-skill-packaging/scripts/ + tests/ |
| `scripts/<internal-component>/adapters/base.py` | skill-owned | 5-rick-ai-<internal-component>-workflow | 5-rick-ai-<internal-component>-workflow | move into .agents/skills/5-rick-ai-<internal-component>-workflow/scripts/ + tests/ |
| `scripts/<internal-component>/core/__init__.py` | skill-owned | 0-detachable-skill-packaging | 0-detachable-skill-packaging,<teammate>-code-review | move into .agents/skills/0-detachable-skill-packaging/scripts/ + tests/ |
| `scripts/<internal-component>/core/entities.py` | skill-owned | cfo-finance-director | cfo-finance-director | move into .agents/skills/cfo-finance-director/scripts/ + tests/ |
| `scripts/<internal-component>/ingest_finance_sheet.py` | skill-owned | 4-cost-allocation-negotiation-protocol | 4-cost-allocation-negotiation-protocol | move into .agents/skills/4-cost-allocation-negotiation-protocol/scripts/ + tests/ |
| `scripts/<internal-component>/tests/conftest.py` | skill-owned | 5-rick-ai-<internal-component>-workflow | 5-rick-ai-<internal-component>-workflow | move into .agents/skills/5-rick-ai-<internal-component>-workflow/scripts/ + tests/ |
| `scripts/<internal-component>/tests/contract/__init__.py` | skill-owned | 0-detachable-skill-packaging | 0-detachable-skill-packaging,<teammate>-code-review | move into .agents/skills/0-detachable-skill-packaging/scripts/ + tests/ |
| `scripts/<internal-component>/tests/contract/test_invariants.py` | skill-owned | 4-cost-allocation-negotiation-protocol | 4-cost-allocation-negotiation-protocol,cfo-finance-director | move into .agents/skills/4-cost-allocation-negotiation-protocol/scripts/ + tests/ |
| `scripts/<internal-component>/tests/integration/__init__.py` | skill-owned | 0-detachable-skill-packaging | 0-detachable-skill-packaging,<teammate>-code-review | move into .agents/skills/0-detachable-skill-packaging/scripts/ + tests/ |
| `scripts/<internal-component>/tests/unit/__init__.py` | skill-owned | 0-detachable-skill-packaging | 0-detachable-skill-packaging,<teammate>-code-review | move into .agents/skills/0-detachable-skill-packaging/scripts/ + tests/ |
| `scripts/ga4_setup_diagnostic.py` | skill-owned | 4-ga4-admin-diagnostic | 4-ga4-admin-diagnostic | move into .agents/skills/4-ga4-admin-diagnostic/scripts/ + tests/ |
| `scripts/gap_effort_calculator.py` | skill-owned | 2-so-what-outcome-ladder | 2-so-what-outcome-ladder,outcome-designer | move into .agents/skills/2-so-what-outcome-ladder/scripts/ + tests/ |
| `scripts/gtm_container_diagnostic.py` | skill-owned | 4-gtm-container-diagnostic | 4-gtm-container-diagnostic | move into .agents/skills/4-gtm-container-diagnostic/scripts/ + tests/ |
| `scripts/land_to_main.py` | skill-owned | 5-land-to-main-mechanical | 5-land-to-main-mechanical | move into .agents/skills/5-land-to-main-mechanical/scripts/ + tests/ |
| `scripts/reasoning_log/__init__.py` | skill-owned | 0-detachable-skill-packaging | 0-detachable-skill-packaging,<teammate>-code-review | move into .agents/skills/0-detachable-skill-packaging/scripts/ + tests/ |
| `scripts/reasoning_log/graph.py` | skill-owned | 0-align-skill-name-and-trigger-to-jtbd | 0-align-skill-name-and-trigger-to-jtbd,0-browser-automation-dispatch,0-changelog-release-notes | move into .agents/skills/0-align-skill-name-and-trigger-to-jtbd/scripts/ + tests/ |
| `scripts/reasoning_log/query.py` | skill-owned | 2-incident-duckdb-analysis | 2-incident-duckdb-analysis,agent-reasoning-log,manager-lead-orchestrator | move into .agents/skills/2-incident-duckdb-analysis/scripts/ + tests/ |
| `scripts/recover_lost_subagent_writes.py` | skill-owned | 1-project-state-checklists | 1-project-state-checklists,1-project-states-best-practices | move into .agents/skills/1-project-state-checklists/scripts/ + tests/ |
| `scripts/test_advising_registry.py` | skill-owned | lisa-client-care-curator | lisa-client-care-curator | move into .agents/skills/lisa-client-care-curator/scripts/ + tests/ |
| `scripts/tests/test_gtm_container_diagnostic.py` | skill-owned | 4-gtm-container-diagnostic | 4-gtm-container-diagnostic | move into .agents/skills/4-gtm-container-diagnostic/scripts/ + tests/ |
| `scripts/validate_agent_skills.py` | skill-owned | 0-agent-prod-safety-autonomy-contract | 0-agent-prod-safety-autonomy-contract,0-align-skill-name-and-trigger-to-jtbd,0-skills-self-improvement | move into .agents/skills/0-agent-prod-safety-autonomy-contract/scripts/ + tests/ |
| `scripts/worktree_disk_guard.py` | skill-owned | 5-sync-github-checklist | 5-sync-github-checklist | move into .agents/skills/5-sync-github-checklist/scripts/ + tests/ |
| `scripts/ym_setup_diagnostic.py` | skill-owned | 4-yandex-metrika-diagnostic | 4-yandex-metrika-diagnostic | move into .agents/skills/4-yandex-metrika-diagnostic/scripts/ + tests/ |
| `scripts/adjust/adjust_quick_export.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/adjust/adjust_raw_data_export.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/adjust/adjust_research_first.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/adjust/analyze_adjust_data.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/advising_clients_symlinks_sync.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/agent_guard.sh` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/agent_scorecard.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/artefact_comparison_challenge.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/askona_matrasy_leverage_writer.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/audio/transcribe_audio.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/audit_client_folder_structure.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/audit_data_quality.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/audit_deep_cross_check.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/audit_gsheets_content.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/audit_reconciliation.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/backfill_registry_telegram_chats.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_bigquery_full_export.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_bronze_to_canonical_silver.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_clean_template_sheet.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_cohort_pnl_calculate.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_create_sheet_from_template.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_deliver_to_google_sheet.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_fill_google_sheet.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_materialize_via_laba.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bcs_verify_and_build_silver.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/bootstrap_kant_ru_drive.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/calculate_process_metrics.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/check_agents_md_anchor_refs.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/check_bronze_hashes.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/check_parquet.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/check_release_status.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/check_sync_status.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/check_utf8_hygiene.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/classify_skills_tool_vs_skill.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/constants.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/helpers.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/sheet_manager.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/template_writer.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/adapters/bcs.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/core/allocator.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/core/formulas.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/core/methodology.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/core/rules.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/tests/integration/test_bcs_adapter.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/tests/unit/test_formulas.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/tests/unit/test_ingest_cli.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/tests/unit/test_methodology.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/<internal-component>/tests/unit/test_rules.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/cpr_adoption_audit.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/create-symlinks.sh` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/data/bronze_data_analyzer.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/data/bronze_data_working.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/data/create_segmented_json.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/data/generate_segmented_json.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/enrich_beads_tickets.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/export/export_with_existing_credentials.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/export_full_csv.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/fix_etl_and_regenerate.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/generate_sales_heroes_season2_v16_reviews.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/generate_yandex_csv_variants.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/get_widgets_data.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/gsheets/check_gsheets_auth.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/gsheets/demo_gsheets_export.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/gsheets/export_parquet_to_gsheets.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/identity_graph_build.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/inject_language_policy_to_all_skills.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/inject_reasoning_log_to_all_skills.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/n8n_leads_flow_monitor.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/packaging_process_watchdog.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/parquet_to_single_json.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/pdf/advanced_pdf_extractor.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/pdf/extract_pdf_text.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/pdf/improved_pdf_extractor.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/productheroes/course_graph_to_mermaid.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/productheroes/course_graph_validate.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/promote_lisa_across_advising.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/reasoning_log/migrate_skill_boilerplate.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/reasoning_log/rollup.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/reasoning_log/test_concurrent.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/reasoning_log/test_find_divergence.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rename_long_files.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rick_widget_flatten.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/build_vipavenue_transaction_item_gold.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/clean_rickai_clients.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/create_classification_symlinks.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/figma_semantic_naming_cpr.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/fix_pilots_structure.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/save_clients_data.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/validate_rickai_structure.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/validate_vipavenue_transaction_item_gold.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rickai/vipavenue_bronze_analysis.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/rotate_settings_snapshots.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/run_export_pipeline.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/run_lightrag_g_pilot.sh` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/sync_dod_check.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/test_bead_lifecycle_advance.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/test_branch_lifecycle_sweep.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/test_divergence_hook_merge_base.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/tests/test_identity_graph_build.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/upload_to_gsheets.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/wire_required_skill_into_agents.py` | orphan | — | no references found | human triage: owning skill? infra? delete? |
| `scripts/lib/leverage_calc.py` | shared-lib | — | imported by 1 scripts | keep as shared lib OR co-locate with primary consumer skill |
| `scripts/<internal-component>/__main__.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/data/compare_json_disk_structure.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/data/compare_json_parquet.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/data/show_parquet_data.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/debug_workflow.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/deep_inspect_bronze.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/inspect_bronze.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/inspect_json_revenue.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/inspect_updated_widget.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/read_bcs_sheet_structure.py` | legacy-oneoff | — | name heuristic (temp/debug/inspect) | archive / delete (one-off) |
| `scripts/temp/temp_analyze_workflow.py` | legacy-oneoff | — | scripts/temp/ | archive / delete (throwaway) |
| `scripts/temp/temp_bronze_explorer.py` | legacy-oneoff | — | scripts/temp/ | archive / delete (throwaway) |
| `scripts/temp/temp_screenshot.py` | legacy-oneoff | — | scripts/temp/ | archive / delete (throwaway) |
| `scripts/bead_lifecycle_advance.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/beads/_lib.sh` | infra | — | infra subdir scripts/beads/ | keep at top-level (workspace plumbing) |
| `scripts/beads/start-beads-dashboard.sh` | infra | — | infra subdir scripts/beads/ | keep at top-level (workspace plumbing) |
| `scripts/beads/start-beads-graph-api.sh` | infra | — | infra subdir scripts/beads/ | keep at top-level (workspace plumbing) |
| `scripts/beads/start-beads-hub.sh` | infra | — | infra subdir scripts/beads/ | keep at top-level (workspace plumbing) |
| `scripts/beads/start-beads-supabase-sync.sh` | infra | — | infra subdir scripts/beads/ | keep at top-level (workspace plumbing) |
| `scripts/beads/start-beads-web.sh` | infra | — | infra subdir scripts/beads/ | keep at top-level (workspace plumbing) |
| `scripts/beads/start-beadsmap.sh` | infra | — | infra subdir scripts/beads/ | keep at top-level (workspace plumbing) |
| `scripts/branch_lifecycle_sweep.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/build_sales_marketing_course_site.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/check_bd_title_shape.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/check_no_oversized_files.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/check_packaging_guards.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/cleanup_client_generated_artifacts.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/cleanup_runtime_artifacts.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/cursor/configure_cursor_autorun.py` | infra | — | infra subdir scripts/cursor/ | keep at top-level (workspace plumbing) |
| `scripts/cursor/purge_cursor_memory.sh` | infra | — | infra subdir scripts/cursor/ | keep at top-level (workspace plumbing) |
| `scripts/git/check_runtime_git_intents.py` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/commit.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/commit_local_changes.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/daily_main_workspace_sync.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/fix_git_force.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/force_push_replit_agent.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/full_remote_sync.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/push_to_replit_agent.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/safe_force_push.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/sync.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git/sync_replit_agent.sh` | infra | — | infra subdir scripts/git/ | keep at top-level (workspace plumbing) |
| `scripts/git_workspace_inventory.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/github/check_github_links_compliance.py` | infra | — | infra subdir scripts/github/ | keep at top-level (workspace plumbing) |
| `scripts/heroes_management_digest.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/incidents/build_parquet.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/incidents/query.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/install_disk_monitor.sh` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/launchd/install.sh` | infra | — | infra subdir scripts/launchd/ | keep at top-level (workspace plumbing) |
| `scripts/make_worktree.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/owner_link.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/packaging_process_watchdog.sh` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/reasoning_log/append.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/reasoning_log/transcript_ingest.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/root_structure_router.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/sales_marketing_tunnel_watchdog.sh` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/setup/bootstrap.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/build_sandbox_client_views.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/configure_git_rick_ai_credential.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/cowork_session_bootstrap.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/git_config_merge_drivers.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/install_beads.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/install_lefthook.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/merge_jsonl_union.py` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/register_hooks.py` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/setup-figma-mcp.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/setup/setup_git_hooks.sh` | infra | — | infra subdir scripts/setup/ | keep at top-level (workspace plumbing) |
| `scripts/structure/validate_structure.py` | infra | — | infra subdir scripts/structure/ | keep at top-level (workspace plumbing) |
| `scripts/system/fix_sudoers.sh` | infra | — | infra subdir scripts/system/ | keep at top-level (workspace plumbing) |
| `scripts/system/install_brew.sh` | infra | — | infra subdir scripts/system/ | keep at top-level (workspace plumbing) |
| `scripts/system/install_python312_auto.sh` | infra | — | infra subdir scripts/system/ | keep at top-level (workspace plumbing) |
| `scripts/system/setup_sudo_access_auto.sh` | infra | — | infra subdir scripts/system/ | keep at top-level (workspace plumbing) |
| `scripts/system/setup_sudo_nopasswd.sh` | infra | — | infra subdir scripts/system/ | keep at top-level (workspace plumbing) |
| `scripts/system/setup_venv_python312.sh` | infra | — | infra subdir scripts/system/ | keep at top-level (workspace plumbing) |
| `scripts/system/setup_venv_python313.sh` | infra | — | infra subdir scripts/system/ | keep at top-level (workspace plumbing) |
| `scripts/test_hooks_smoke.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/uv-native.sh` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/validate_skill_contract.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |
| `scripts/verify_tree_completeness.py` | infra | — | Makefile/lefthook/hooks/settings | keep at top-level (wired into build/CI/hooks) |

## Counts per category

- **orphan**: 101
- **infra**: 65
- **skill-owned**: 33
- **legacy-oneoff**: 13
- **shared-lib**: 1
- **total**: 213
