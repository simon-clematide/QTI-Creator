# Deployment & Development Guide

This document covers local setup, development workflows, testing, and deployment to GitHub and Hugging Face Spaces for **QTI-Creator**.

---

## 1. Prerequisites

- **Python 3.10+** (Python 3.10–3.14 supported)
- **Git** with SSH key configured for GitHub and Hugging Face
- Standard command line tools (`bash`, `python3`)

---

## 2. Installation & Local Setup

### Clone Repository
```bash
git clone https://github.com/simon-clematide/QTI-Creator.git
cd QTI-Creator
```

### Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

*(Optional)* If you plan to work with YAML frontmatter parsing, install `pyyaml`:
```bash
pip install pyyaml
```

---

## 3. Development Workflow

### Run Application Locally
Start the Gradio web server with hot reloading enabled for development:
```bash
gradio app.py
```
Or with standard python:
```bash
python3 app.py
```

The app will be accessible at `http://127.0.0.1:7860`.

### Running Tests
Run the complete automated test suite:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

To run individual test modules:
```bash
python3 -m unittest tests/test_preview.py
python3 -m unittest tests/test_parser.py
python3 -m unittest tests/test_qti21.py
python3 -m unittest tests/test_version.py
```

---

## 4. Version Management

The version follows Semantic Versioning (`v0.X.Y`) during the beta phase.
The single source of truth is maintained in `src/version.py`:

```python
__version__ = "0.1.0"
__release_date__ = "2026-09-21"
```

The version and release date are displayed in:
1. The **top header** next to the application title (`v0.X.Y • YYYY-MM-DD`).
2. The **footer** at the bottom of the page.

### Bumping the Version Manually
You can increment the version and set today's release date at any time:

```bash
# Increment patch version (0.1.0 -> 0.1.1):
python3 scripts/bump_version.py patch

# Increment minor version (0.1.0 -> 0.2.0):
python3 scripts/bump_version.py minor

# Increment major version (0.1.0 -> 1.0.0):
python3 scripts/bump_version.py major
```

---

## 5. Pushing & Deployment

QTI-Creator maintains two primary git remotes:
- `origin`: GitHub repository (`git@github.com:simon-clematide/QTI-Creator.git` or HTTPS)
- `space`: Hugging Face Space (`git@hf.co:spaces/simon-clmtd/qti-creator`)

### Verifying Git Remotes
```bash
git remote -v
```
Expected output:
```text
origin  git@github.com:simon-clematide/QTI-Creator.git (fetch)
origin  git@github.com:simon-clematide/QTI-Creator.git (push)
space   git@hf.co:spaces/simon-clmtd/qti-creator (fetch)
space   git@hf.co:spaces/simon-clmtd/qti-creator (push)
```

If `space` is missing, configure it with:
```bash
git remote add space git@hf.co:spaces/simon-clmtd/qti-creator
```

---

### Deploying to Hugging Face Space

Every deployment to Hugging Face triggers an automatic version bump (`v0.X.Y`) and date update.

#### Option A: Using the Deployment Script (Recommended)
```bash
./scripts/push_to_hf.sh [patch|minor|major]
```
By default, this bumps the patch version, creates a release commit, and pushes to `space main`.

#### Option B: Direct Git Push (Pre-Push Hook)
The repository includes a Git pre-push hook in `.git/hooks/pre-push`. Whenever you push to the `space` remote:
```bash
git push space main
```
The hook automatically:
1. Detects that the destination is Hugging Face.
2. Runs `scripts/bump_version.py patch`.
3. Creates a `chore(release): bump version to v0.X.Y` commit.
4. Completes the push with the updated version.

---

### Pushing to GitHub
To push your development commits to GitHub:
```bash
git push origin main
```
*(Pushing to `origin` does not auto-increment the version unless you push to `space`).*

---

## 6. Deployment Checklist

Before pushing a new release:
1. Run all tests: `python3 -m unittest discover -s tests -p "test_*.py"`
2. Verify git working tree: `git status`
3. Push to Hugging Face: `./scripts/push_to_hf.sh` (or `git push space main`)
4. Sync GitHub with the release commit: `git push origin main`
