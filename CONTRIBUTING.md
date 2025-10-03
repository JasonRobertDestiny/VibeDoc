# Contributing to VibeDoc

First off, thank you for considering contributing to VibeDoc! It's people like you that make VibeDoc such a great tool.

## 🌟 Ways to Contribute

### 🐛 Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and what you expected**
- **Include screenshots if relevant**
- **Include your environment details** (OS, Python version, etc.)

### ✨ Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use a clear and descriptive title**
- **Provide a detailed description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List any similar features in other tools**

### 🔧 Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Write clear commit messages**
6. **Submit a pull request** with a comprehensive description

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Virtual environment tool (venv or conda)

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/VibeDoc.git
cd VibeDoc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Start the application
python app.py
```

## 📝 Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length**: Maximum 120 characters
- **Docstrings**: Use Google style docstrings
- **Type hints**: Use type hints for all functions
- **Naming**: Use descriptive names, avoid abbreviations

### Code Example

```python
def generate_development_plan(
    user_idea: str, 
    reference_url: str = ""
) -> Tuple[str, str, Optional[str]]:
    """
    Generate a comprehensive development plan from user input.
    
    Args:
        user_idea: User's product concept description
        reference_url: Optional URL for additional context
        
    Returns:
        Tuple containing:
        - Generated development plan (str)
        - AI coding prompts (str)
        - Temporary file path or None (Optional[str])
        
    Raises:
        ValueError: If user_idea is empty or invalid
        APIError: If AI service call fails
    """
    # Implementation here
    pass
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body

footer
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(export): add PDF export with custom templates

- Implement PDF generation using reportlab
- Add template selection in UI
- Include logo and branding options

Closes #123
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_generator.py

# Run specific test
pytest tests/test_generator.py::test_generate_plan
```

### Writing Tests

```python
import pytest
from app import generate_development_plan

def test_generate_plan_with_valid_input():
    """Test plan generation with valid user input."""
    result = generate_development_plan(
        user_idea="Create a task management app",
        reference_url=""
    )
    assert result is not None
    assert len(result[0]) > 100  # Plan should be substantial

def test_generate_plan_with_empty_input():
    """Test error handling for empty input."""
    with pytest.raises(ValueError):
        generate_development_plan(user_idea="")
```

## 📚 Documentation

### Documentation Standards

- **Keep it simple**: Write for beginners
- **Use examples**: Show, don't just tell
- **Keep it updated**: Update docs with code changes
- **Be comprehensive**: Cover edge cases and common issues

### Documentation Locations

- **README.md**: Project overview and quick start
- **docs/**: Detailed documentation
- **Inline comments**: Explain complex logic
- **Docstrings**: For all public functions

## 🔍 Code Review Process

1. **Automated checks** must pass (tests, linting)
2. **At least one approval** from maintainers required
3. **Address feedback** promptly and professionally
4. **Squash commits** before merging (we'll help with this)

## 🎨 UI/UX Contributions

### Design Guidelines

- **Consistency**: Follow existing design patterns
- **Accessibility**: WCAG 2.1 AA compliance
- **Responsiveness**: Support mobile and desktop
- **Performance**: Optimize images and assets

### UI Testing

Test your UI changes on:
- Desktop browsers (Chrome, Firefox, Safari)
- Mobile devices (iOS Safari, Chrome)
- Dark and light themes
- Different screen sizes

## 🌍 Internationalization

We welcome translations! To add a new language:

1. Create `locale/[language_code]/LC_MESSAGES/`
2. Copy `messages.pot` as `messages.po`
3. Translate strings
4. Test thoroughly
5. Submit PR

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 💬 Questions?

- **GitHub Discussions**: For general questions
- **GitHub Issues**: For specific bugs or features
- **Email**: johnrobertdestinv@gmail.com for private inquiries
- **Demo Video**: [Watch on Bilibili](https://www.bilibili.com/video/BV1ieagzQEAC/)

## 🙏 Thank You!

Your contributions make VibeDoc better for everyone. We appreciate your time and effort!

---

**Happy Contributing! 🎉**
