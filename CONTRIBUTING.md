# Contributing

Bug reports, documentation improvements, tests, and focused code changes are
welcome. First-time contributors are welcome too.

## Before You Start

Small fixes can be submitted directly as pull requests. This includes typos,
documentation corrections, and focused bug fixes with regression tests.

For new features or significant changes, open an issue to discuss the problem
and proposed approach before starting implementation. Examples include agent
workflow changes, public API changes, new provider integrations, and broad
refactoring.

Check existing issues and pull requests to avoid duplicating work.

## Backend Development

Use Python 3.10 or later; CI currently uses Python 3.10. Fork the repository,
create a branch, and create and activate a virtual environment before installing
dependencies.

```sh
python -m pip install -r requirements.txt
python -m pip install ruff
python -m ruff check backend --select E9,F63,F7,F82
```

The Ruff command above matches the current CI check. To run the API locally,
also install its optional dependencies:

```sh
python -m pip install fastapi "uvicorn[standard]"
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Before starting the API, copy [env.example](env.example) to `.env` and configure
the providers needed for your work. See the [README](README.md#quick-start) for
configuration and request examples.

## Frontend Development

The React widget is a separate npm package:

```sh
cd frontend/travel-widget
npm ci
npm run build
```

Use `npm start` from that directory for local development.

## Testing

The backend `tests/unit` and `tests/integration` directories currently contain
only scaffolding, and CI does not yet run a backend test suite. Add focused
regression tests for behavior changes rather than assuming existing coverage.
When adding Python tests, install pytest and run them from the repository root:

```sh
python -m pip install pytest
python -m pytest tests
```

Mock LLM and external provider calls in automated tests by default. If you run
live integration checks, describe which providers were used and any costs or
side effects. Do not send real SMS messages or modify CRM records without
explicit authorization.

For frontend changes, run the production build and verify the affected widget
flow. Add or update frontend tests when applicable.

## Pull Requests

- Keep each PR focused on one problem. Avoid unrelated refactoring or formatting.
- Explain what changed, why it is needed, and any user-visible behavior changes.
- Link the relevant issue when one exists.
- Add or update tests for behavior changes and documentation for affected usage.
- Include the verification commands and results. If a check was not run, say why.
- Follow the existing code style and keep CI checks passing.
- Redact API keys, credentials, customer details, and other personal information
  from examples, logs, and screenshots. Never commit `.env` files.

Maintainers may request changes. Be prepared to explain your implementation and
address review feedback.

## AI-Assisted Contributions

AI-assisted contributions are welcome and follow the same standards as other
contributions. Review every change, understand how it works, run relevant tests,
and verify that it follows the repository's existing style.

Do not submit bulk, unreviewed generated content. You are responsible for the
correctness of your submission and for having the right to contribute it.

## License

By submitting a contribution, you agree to license it under this repository's
[MIT License](LICENSE).
