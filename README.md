# 29oct_2

## Flask Server Migration Project

This project is a complete migration of a Node.js server to Python 3 using Flask, preserving all functionalities of the original project.

## Technology Stack

- **Python**: 3.12
- **Framework**: Flask 3.1.2
- **ORM**: SQLAlchemy 2.0.35
- **Testing**: pytest 8.3.3
- **Database**: PostgreSQL (with SQLite for testing)

## Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- virtualenv (optional but recommended)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd 29oct_2
```

### 2. Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
# Install core application dependencies
pip install -r requirements.txt

# Install testing dependencies (includes core dependencies)
pip install -r requirements-test.txt

# Install development dependencies (includes testing dependencies)
pip install -r requirements-dev.txt
```

## Testing

This project uses pytest as the primary testing framework with comprehensive test coverage requirements.

### Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── unit/                    # Unit tests (fast, isolated)
│   ├── routes/             # API route handler tests
│   ├── services/           # Business logic service tests
│   ├── models/             # Data model tests
│   ├── utils/              # Utility function tests
│   └── middleware/         # Middleware tests
├── integration/            # Integration tests (database, external services)
├── functional/             # End-to-end workflow tests
├── fixtures/               # Shared test data and fixtures
├── mocks/                  # Mock implementations
└── helpers/                # Test helper functions
```

### Running Tests

#### Run All Tests

```bash
pytest
```

#### Run Tests with Verbose Output

```bash
pytest -v
```

#### Run Specific Test File

```bash
pytest tests/unit/services/test_user_service.py
```

#### Run Specific Test Function

```bash
pytest tests/unit/services/test_user_service.py::test_create_user_with_valid_data
```

#### Run Tests by Marker

```bash
# Run only unit tests
pytest -m "unit"

# Run only integration tests
pytest -m "integration"

# Run only API tests
pytest -m "api"

# Skip slow tests
pytest -m "not slow"
```

### Test Markers

The following pytest markers are available for test categorization:

- `unit`: Unit tests (fast, isolated)
- `integration`: Integration tests (slower, with database)
- `functional`: Functional tests (end-to-end workflows)
- `slow`: Tests that take >1 second
- `smoke`: Critical smoke tests
- `api`: API endpoint tests
- `database`: Tests requiring database
- `external`: Tests involving external services (mocked)

### Code Coverage

#### Measure Coverage

```bash
# Run tests with coverage report
pytest --cov=app

# Show missing lines in coverage
pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html  # View in browser
```

#### Coverage Targets

| Component | Minimum Coverage | Target Coverage |
|-----------|-----------------|-----------------|
| Overall | 85% | 90% |
| API Routes | 90% | 95% |
| Business Logic | 85% | 95% |
| Authentication | 100% | 100% |
| Authorization | 100% | 100% |
| Data Models | 85% | 90% |

#### Enforce Coverage Threshold

```bash
# Fail if coverage is below 85%
pytest --cov=app --cov-fail-under=85
```

### Parallel Test Execution

For faster test execution, run tests in parallel:

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU cores)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

### Test Environment Configuration

Tests use the `.env.test` file for environment configuration. This file is automatically loaded by the test fixtures.

Key test environment variables:
- `FLASK_ENV=testing`
- `TESTING=True`
- `DATABASE_URL=sqlite:///:memory:` (in-memory database for fast tests)
- `SECRET_KEY=test-secret-key-not-for-production`

### Writing Tests

#### Test Naming Convention

- Test files: `test_*.py`
- Test functions: `test_<action>_<expected_result>()`
- Test classes: `class Test<Feature>:`

#### Example Test

```python
import pytest

@pytest.mark.unit
def test_user_creation_with_valid_data(db_session):
    """Test that a user can be created with valid data."""
    user_data = {
        'email': 'test@example.com',
        'password': 'SecurePass123!',
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    user = UserService.create(user_data)
    
    assert user.id is not None
    assert user.email == 'test@example.com'
    assert user.first_name == 'Test'
    assert 'password' not in user.__dict__
```

### Continuous Testing During Development

Use pytest-watch for continuous testing:

```bash
pip install pytest-watch
ptw  # Watches for file changes and re-runs tests
```

## Development Workflow

### Code Quality Tools

The project includes the following development tools:

- **black**: Code formatting (PEP 8 compliance)
- **flake8**: Linting and style checking
- **mypy**: Static type checking
- **isort**: Import sorting
- **pre-commit**: Git hooks for automated code quality checks

### Format Code

```bash
black app/ tests/
isort app/ tests/
```

### Run Linting

```bash
flake8 app/ tests/
```

### Type Checking

```bash
mypy app/
```

## CI/CD Integration

Tests are automatically run in the CI/CD pipeline on:
- Pull requests
- Commits to main branch
- Nightly builds

CI/CD checks include:
- ✅ All tests pass
- ✅ Coverage >= 85%
- ✅ No linting errors
- ✅ Code properly formatted
- ✅ Type checks pass

## Project Status

This project is currently in the migration phase:

- ✅ Testing infrastructure setup complete
- ✅ Python 3.12 environment configured
- ✅ Flask 3.1.2 and dependencies installed
- ✅ pytest testing framework configured
- ⏳ Flask application implementation pending
- ⏳ Test suite development pending
- ⏳ Migration validation pending

## Contributing

### Testing Requirements for Contributors

When contributing to this project:

1. **Write tests** for all new features
2. **Maintain coverage** at or above 85%
3. **Run full test suite** before submitting PR: `pytest`
4. **Ensure all tests pass**: No failing tests allowed
5. **Follow test conventions**: Use pytest markers, proper naming
6. **Update documentation**: Document any new test fixtures or patterns

### Running Pre-commit Checks

```bash
# Install pre-commit hooks
pre-commit install

# Run all checks manually
pre-commit run --all-files
```

## License

[License information to be added]

## Contact

[Contact information to be added]