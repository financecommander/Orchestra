# Contributing to Orchestra

Thank you for your interest in contributing to Orchestra! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Issue Templates](#issue-templates)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/Orchestra.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit your changes: `git commit -m "Add feature: description"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a Pull Request

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Your environment (OS, Python version, etc.)

### Feature Requests

Use the feature request issue template to propose new features. Feature requests will be automatically processed by the Orchestra workflow system.

### Code Contributions

1. Check existing issues and PRs to avoid duplicates
2. Discuss major changes in an issue first
3. Follow the coding standards
4. Add tests for new functionality
5. Update documentation as needed

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip or poetry for package management

### Installation

```bash
# Clone the repository
git clone https://github.com/financecommander/Orchestra.git
cd Orchestra

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=orchestra --cov-report=html
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .
pylint orchestra

# Type checking
mypy orchestra
```

## Pull Request Process

1. **Update Documentation**: Ensure any new features or changes are documented
2. **Add Tests**: Include tests that cover your changes
3. **Code Quality**: Ensure all linting and tests pass
4. **Commit Messages**: Write clear, descriptive commit messages
5. **PR Description**: Provide a detailed description of your changes
6. **Review Process**: Address review feedback promptly

### PR Checklist

Before submitting your PR, ensure:

- [ ] Code follows the project's style guidelines
- [ ] Tests have been added/updated and pass
- [ ] Documentation has been updated
- [ ] Commit messages are clear and descriptive
- [ ] No unnecessary files are included
- [ ] The PR addresses a single concern

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for function signatures
- Write docstrings for all public modules, functions, classes, and methods
- Keep functions focused and small
- Use meaningful variable and function names

### Example

```python
from typing import List, Optional


def process_workflow(
    workflow_name: str,
    parameters: Optional[dict] = None
) -> List[str]:
    """
    Process a workflow with given parameters.
    
    Args:
        workflow_name: Name of the workflow to process
        parameters: Optional dictionary of workflow parameters
        
    Returns:
        List of execution results
        
    Raises:
        ValueError: If workflow_name is empty
    """
    if not workflow_name:
        raise ValueError("Workflow name cannot be empty")
    
    # Implementation here
    return []
```

### Testing Standards

- Write unit tests for all new functionality
- Aim for high test coverage (>80%)
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Mock external dependencies

### Documentation Standards

- Keep README.md up to date
- Document all public APIs
- Include examples in docstrings
- Update CHANGELOG.md for significant changes

## Issue Templates

### Feature Request Template

When creating a feature request, use the provided template which includes:
- Feature description
- Use case
- Expected behavior
- Additional context

Feature requests with the `orchestra-trigger` label will automatically trigger the Orchestra workflow system for evaluation and implementation.

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the `question` label
- Reach out to the maintainers

## License

By contributing to Orchestra, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Orchestra! 🎵
