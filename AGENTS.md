# AGENTS.md — AI Agent Guide for QTI-Creator

Guidelines and facts for AI coding agents working in this repository.

---

## Repository Layout

```
src/              Core library (parser, generator, validator, version)
qti_creator/      Gradio UI layer
tests/            Automated test suite (unittest / pytest)
scripts/          CLI helpers (bump_version.py, push_to_hf.sh, validate_qti.py)
sample_quizzes/   Example .quizmd / .zip fixtures
```

---

## Version Management

**Single source of truth:** [`src/version.py`](src/version.py)

```python
__version__ = "1.0.4"
__release_date__ = "2026-09-29"
```

The version string follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`).

### Bumping the version

Use the dedicated script — never edit `src/version.py` by hand across concurrent changes:

```bash
python3 scripts/bump_version.py patch   # 1.0.3 → 1.0.4
python3 scripts/bump_version.py minor   # 1.0.4 → 1.1.0
python3 scripts/bump_version.py major   # 1.1.0 → 2.0.0
```

The script updates both `__version__` and `__release_date__` (today's date).

### Commit convention for version bumps

```
chore: bump version to X.Y.Z
```

---

## Git Remotes

| Remote   | URL                                              | Notes                                      |
|----------|--------------------------------------------------|--------------------------------------------|
| `origin` | `git@github.com:simon-clematide/QTI-Creator.git` | Primary development remote                 |
| `space`  | `git@hf.co:spaces/simon-clmtd/qti-creator`      | Hugging Face Space (triggers auto-deploy)  |

### Hugging Face auto-bump behaviour

A **pre-push hook** (`.git/hooks/pre-push`) fires automatically on every push to `space`.  
It runs `scripts/bump_version.py patch`, creates a `chore(release): bump version to vX.Y.Z` commit, and then completes the push.  
**Consequence:** the version seen on HF will always be one patch ahead of what you committed locally.  
Push order that avoids drift: push to `origin` first, then push to `space`.

---

## Running Tests

```bash
# Full suite
pytest

# Single module
pytest tests/test_jqtiplus.py

# With unittest
python3 -m unittest discover -s tests -p "test_*.py"
```

JQTI+ integration tests (`TestJqtiPlusRuntimeValidation`) require Java 17+ on `$PATH`.  
On first run the runner fetches and caches OpenOLAT Nexus JARs automatically.

---

## Deployment Checklist

1. Run full test suite and confirm it passes.
2. Bump the patch version: `python3 scripts/bump_version.py patch`
3. Commit: `git commit -m "chore: bump version to X.Y.Z"`
4. Push to GitHub: `git push origin main`
5. Push to Hugging Face: `git push space main`  
   *(The pre-push hook will bump the version once more and create an extra commit.)*
6. Pull back the auto-bump commit: `git pull origin main` (if you need local parity).

Or use the all-in-one script:

```bash
./scripts/push_to_hf.sh [patch|minor|major]
```
