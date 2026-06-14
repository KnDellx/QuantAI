# AGENTS.md

## Role

You are working in this repository as a careful coding agent.

## General rules

- Use minimal changes.
- Do not refactor unrelated files.
- Do not introduce new production dependencies without asking.
- Do not modify secrets, credentials, or `.env` files.
- Do not change database schema unless explicitly requested.
- Before editing, inspect relevant files and make a short plan.
- After editing, summarize changed files and test results.

## Development workflow

- API-first: define request/response schema before implementation.
- Keep PRs small and reviewable.
- All business logic must be testable.
- Code must be easy to roll back.
- Do not hide errors with broad `except Exception` unless re-raising or logging properly.

## Python stack

- Python 3.11+
- Use `uv` for dependency management.
- Use FastAPI for APIs.
- Use Pydantic models for request and response schemas.
- Use Ruff for linting and import sorting.
- Use Black-compatible formatting.
- All public API functions must have type hints.
- No unused variables.
- No unused imports.
- No unhandled errors.

## Python project structure

backend/
  app/
    api/
    service/
    model/
    core/
    main.py
  tests/

## Python commands

- Install dependencies: `uv sync`
- Add dependency: `uv add <package>`
- Run app: `uv run uvicorn backend.app.main:app --reload`
- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Fix lint: `uv run ruff check . --fix`
- Test: `uv run pytest`

## Node.js stack

- Node.js 18+
- Use Express or NestJS.
- Use ESLint for code quality.
- Use Prettier for formatting.
- Use async/await consistently.
- API layer must be separated from service layer.
- No unused variables.

## Node.js project structure

frontend/ or service/
  src/
    routes/
    controllers/
    services/
    utils/

## Node commands

- Install: `npm install`
- Dev: `npm run dev`
- Lint: `npm run lint`
- Format: `npm run format`
- Test: `npm test`

## API rules

- Python FastAPI must use Pydantic request/response models.
- FastAPI docs must be available at `/docs`.
- Node APIs must include Swagger annotations where applicable.
- Do not implement API endpoints without schema definition.

## README requirement

Every service must include:

1. Overview
2. Tech Stack
3. Setup
4. Environment Variables
5. Run Locally
6. API Docs
7. Deployment

## Branching

- `main` is production.
- `dev` is integration.
- Feature branches: `feat/<name>`
- Hotfix branches: `hotfix/<name>`

## Quality gate before merge

Do not mark a task done unless:

- Lint passes.
- Format check passes.
- Tests pass or failure is clearly reported.
- API schema is defined.
- README or docs are updated when behavior changes.