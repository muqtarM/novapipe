# Contributing to NovaPipe

Thank you for your interest in contributing to NovaPipe! We welcome contributions from everyone. Please take a moment to read this guide before you submit any pull requests.

---

## Code of Conduct

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please review it to ensure a welcoming environment.

---

## Getting Started

1. **Fork** the repository on GitHub.  
2. **Clone** your fork:
   ```bash
   git clone https://github.com/<your-username>/novapipe.git
   cd novapipe
   ```
3. **Install dependencies**:
   ```bash
   poetry install          # with Poetry
   # or
   pip install -e .[dev]   # with pip
   ```
4. **Set up your environment**:
   - Python 3.8+  
   - Ensure you have `pre-commit` hooks enabled (optional).

---

## Branching & Workflow

- Use the **main** branch for stable releases.  
- Create feature branches from **main** named `feature/<short-description>`.  
- Commit messages should follow Conventional Commits:  
  ```
  feat(cli): add new `novapipe report` command
  fix(core): handle empty pipeline file gracefully
  chore(release): bump version to v1.0.0
  ```

---

## Writing Code

- Follow existing **style**:  
  - **Black** for formatting (`black src/ tests/`)  
  - **Mypy** for type checking  
  - **Flake8** for linting  
- Write **docstrings** in Google style or Markdown, and include an **Example:** section when relevant.

---

## Testing

- Write **unit tests** under `tests/` for new functionality.  
- For external services, use **fixtures** (e.g., `moto` for AWS S3).  
- Run tests with coverage:
  ```bash
  pytest --cov=novapipe
  ```
- Ensure **100% coverage** for new code, and keep overall coverage above the project threshold.

---

## Documentation

- All CLI commands are documented via **mkdocstrings** in `docs/cli.md`.  
- For new public APIs, add examples to **`docs/quickstart.md`** or create pages under **`docs/advanced/`**.  
- Run the docs locally:
  ```bash
  mkdocs serve
  ```

---

## Pull Requests

1. **Fork & create a branch** for your change.  
2. **Commit** your work with clear messages.  
3. **Push** to your fork.  
4. **Open** a pull request against `main`.  

We use GitHub Actions to test PRs automatically. Once your changes pass CI and have been reviewed, you’ll be merged.

---

## Issues & Feature Requests

- **Bug reports**: Open an issue under the **“Bug Reports”** category. Provide reproduction steps.  
- **Feature requests**: Use the **“Feature Requests”** category. Provide motivation and example usage.

---

## Thank You!

Thanks for helping improve NovaPipe! Your contributions make the project better for everyone.  
