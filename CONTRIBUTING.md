# Contributing to OpenRouter Checker

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project is committed to providing a welcoming and inspiring community for all.
Please read and adhere to our Code of Conduct.

Behavior we do NOT tolerate:
- Harassment, discrimination, or abuse
- Insults, threats, or dehumanizing language
- Unwelcome sexual attention or advances
- Doxxing or publishing private information
- Other conduct unethical or unprofessional

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Setup Development Environment

```bash
git clone https://github.com/clashssd/openrouter-checker.git
cd openrouter-checker
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Running Tests

```bash
python ai/test.py
```

Expected output: 22 tests passing

### Code Style

This project uses:
- **Black** for code formatting
- **Flake8** for linting
- **Mypy** for type checking

Run before committing:

```bash
black ai/
flake8 ai/
mypy ai/ --ignore-missing-imports
```

## Development Workflow

### 1. Create an Issue

Before starting work, create an issue describing:
- What problem you're solving
- Why it's needed
- Proposed solution (optional)

### 2. Fork the Repository

Click "Fork" on GitHub to create your fork.

### 3. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/streaming-improvements`
- `fix/rate-limit-bug`
- `docs/api-reference-update`

### 4. Make Your Changes

- Write clean, readable code
- Add comments for complex logic
- Keep commits atomic and descriptive
- One feature per branch/PR

### 5. Add Tests

All new features must have tests. Add to `ai/test.py`:

```python
class TestYourFeature(unittest.TestCase):
    def test_feature_works(self):
        result = your_function()
        self.assertEqual(result, expected)
```

Ensure all tests pass:

```bash
python ai/test.py
```

### 6. Update Documentation

If adding features, update relevant docs:
- README.md
- API_REFERENCE.txt
- EXAMPLES.txt

### 7. Commit Changes

Use descriptive commit messages:

```
feat(chat): add multiline input support

- Support Ctrl+Enter for multiline messages
- Add input buffer management
- Add visual indicator for multiline mode

Fixes #42
```

Format: `<type>(<scope>): <description>`

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Code style (no logic change)
- `refactor` - Code refactoring
- `test` - Test additions
- `chore` - Build, dependencies

### 8. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 9. Create Pull Request

1. Go to GitHub
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill in PR description:
   - What changes were made
   - Why they were needed
   - How to test
   - Related issues

5. Wait for review

### 10. Address Review Comments

1. Make requested changes
2. Commit with message: `fix: address review comments`
3. Push to same branch (automatically updates PR)
4. Reply to comments

### 11. Merge

Maintainers will merge once approved and tests pass.

## Reporting Issues

### Reporting Bugs

Include:
1. Python version: `python --version`
2. OS and version
3. Steps to reproduce
4. Expected behavior
5. Actual behavior
6. Error logs (from `app.log`)
7. Minimal example code

### Requesting Features

Include:
1. Clear description of feature
2. Use case and motivation
3. Proposed API or interface (if applicable)
4. Alternative approaches considered
5. Any additional context

## Code Guidelines

### General

- Write for Python 3.8+ compatibility
- Use type hints for all function parameters
- Add docstrings to all public functions
- Keep functions small and focused
- Maintain <100 line functions

### Example Code Style

```python
from typing import Optional, List, Dict, Any

def process_models(
    models: List[Dict[str, Any]],
    filter_free: bool = True
) -> Optional[List[str]]:
    """
    Process model list and return IDs.
    
    Args:
        models: List of model dictionaries
        filter_free: Whether to filter free models only
        
    Returns:
        List of model IDs or None on error
    """
    if not models:
        logger.warning("No models to process")
        return None
    
    result = []
    for model in models:
        model_id = model.get("id")
        if filter_free and not model_id.endswith(":free"):
            continue
        result.append(model_id)
    
    return result if result else None
```

### Naming Conventions

- `CamelCase` for classes
- `snake_case` for functions and variables
- `UPPER_SNAKE_CASE` for constants
- Prefix private methods with `_`
- Prefix private variables with `_`

### Error Handling

```python
try:
    result = api_call()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

## Testing Guidelines

### Test Structure

```python
import unittest
from core.module import MyClass

class TestMyClass(unittest.TestCase):
    def setUp(self):
        self.instance = MyClass()
    
    def tearDown(self):
        pass
    
    def test_happy_path(self):
        result = self.instance.method()
        self.assertIsNotNone(result)
    
    def test_error_handling(self):
        with self.assertRaises(ValueError):
            self.instance.method(invalid_input)
```

### Test Coverage

Aim for 80%+ coverage

### Test Types

- Unit tests: Test individual functions
- Integration tests: Test component interactions
- Error tests: Test error conditions
- Edge case tests: Test boundary conditions

## Pull Request Process

### Before Submitting

- Code follows style guidelines
- All tests pass (python test.py)
- New tests added for features
- Documentation updated
- No breaking changes
- Commit messages descriptive

### Review Process

1. Maintainer reviews code
2. Provides feedback or approves
3. Address feedback
4. Maintainer re-reviews
5. Merge when approved

Typical review time: 1-7 days

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

## Questions

Feel free to open an issue with the question tag for help.

Thank you for contributing!
