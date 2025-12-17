# todo-refactor-dataset
Sample SWE-Bench refactoring dataset for Todo app
# Todo Refactor Dataset Sample

Sample for SWE-Bench compatible code refactoring dataset. Refactors a messy Flask Todo app with SQLite and auth.

## How to Run
1. Build Docker: `docker build -t todo-refactor .`
2. Run tests: `docker run --rm todo-refactor`
3. Run app (after): `docker-compose up`

Tests verify functionality unchanged but refactoring improves quality.