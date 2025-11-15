# Repository Guidelines

## Project Structure & Module Organization
The Gradio entry point lives in `app.py`, which orchestrates planning (`plan_editor.py`), narrative assembly (`explanation_manager.py`), prompt tuning (`prompt_optimizer.py`), MCP connectivity (`enhanced_mcp_client.py`), and export flows (`export_manager.py`). Configuration and feature toggles sit in `config.py`, pulling secrets from `.env`. Generated assets (mock plans, diagrams) belong in `HandVoice_Development_Plan.md` and `image/`. Containerization artifacts (`Dockerfile`, `docker-compose.yml`) and dependency locks (`requirements.txt`) stay at the repo root for easy CI wiring.

## Build, Test & Development Commands
```bash
python -m venv .venv && source .venv/bin/activate  # create local env
pip install -r requirements.txt                    # sync dependencies
python app.py                                      # launch Gradio dev server on :7860
docker compose up --build                          # full-stack preview with MCP adapters
```
Run manual smoke tests (Generate Plan → Export → Prompt Optimizer) before touching core files, as no automated suite exists yet.

## Coding Style & Naming Conventions
Follow PEP8, 4-space indentation, and keep functions focused on a single responsibility with ≤3 logical nesting levels. All magic numbers/strings must be promoted to named constants in the nearest module scope. Key business logic branches require concise Chinese comments to aid bilingual reviewers. Prefer descriptive snake_case for functions/variables, PascalCase for dataclasses, and kebab-case for asset filenames.

## Testing Guidelines
Until a formal test harness lands, rely on reproducible manual runs: 1) start `python app.py`, 2) feed a known prompt (see `HandVoice_Development_Plan.md`), 3) verify the generated plan, visual exports, and MCP-backed knowledge injection. Document observed results in the PR description, including browser screenshots or exported files when regressions are possible.

## Commit & Pull Request Guidelines
Recent history favors Conventional Commit prefixes (`refactor:`, `feat:`, `docs:`). Keep messages under 72 characters in the subject and explain rationale plus testing notes in the body. Every PR should link relevant GitHub issues, summarize manual test evidence, attach UI diffs or CLI logs, and highlight which modules changed. Avoid force-pushing shared branches.

## Security & Configuration Tips
Never commit `.env` or real API keys; rely on `.env.example` conventions and `config.AppConfig.validate_config()` before deployment. Double-check that MCP endpoints and `SILICONFLOW_API_KEY` load from environment variables in CI. SEO integrations have a hard rule: do not modify `analyzer.py`’s `is_quality_keyword()` implementation (lines 12-89) or any public API contracts that consume it.
