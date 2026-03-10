# Codex Collaboration Guidelines

These instructions apply to the entire repository. Follow them for every pull request.

## Environment Setup
- Use **Python 3.12**.
- Install required packages with `pip install -r requirements.txt` before running tests.

## Development Workflow
- Use Python 3.12 features when helpful but keep compatibility with standard libraries.
- Format changed Python files using `black -l 120 <file>`. Check formatting with `python -m black --check <file>`.
- Run tests with `python -m pytest -q`. Address any failures before submitting.

## Coding Style
- Write clear, single-purpose functions with type hints.
- Document all public functions and classes using triple-quoted docstrings.
- Keep lines under 120 characters and use 4 spaces per indentation level.
- Avoid wildcard imports and unnecessary globals.

## Commit Messages
- Summarize changes in the first line (max 72 characters) using the imperative mood.
- Include a blank line after the summary, followed by any details.
