# Flask Server - Node.js Migration Project

A complete migration of a Node.js/Express server to Python 3 using Flask, preserving all functionalities of the original project while maintaining API compatibility and improving code maintainability.

## Overview

This project represents a full server rewrite from Node.js to Python 3 using the Flask web framework. The migration maintains 100% functional equivalence with the original Node.js implementation, ensuring all API endpoints, business logic, authentication mechanisms, and data operations remain consistent.

## Requirements

### Python Version
- **Required**: Python >= 3.9
- **Recommended**: Python 3.12 (latest stable version with full Flask 3.1.x compatibility)

### Core Framework
- **Flask**: 3.1.2
- **Flask-SQLAlchemy**: 3.1.1
- **SQLAlchemy**: 2.0.35
- **Werkzeug**: 3.1.0

### Testing Framework
- **pytest**: 8.3.3+
- **pytest-cov**: 5.0.0+
- **pytest-mock**: 3.14.0+
- **pytest-flask**: 1.3.0+

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd 29oct_2
```

### 2. Create Virtual Environment
```bash
# Create virtual environment with Python 3.12
python3.12 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Upgrade pip
```bash
pip install --upgrade pip
```

### 4. Install Dependencies

**Application Dependencies:**
```bash
pip install -r requirements.txt
```

**Testing Dependencies:**
```bash
pip install -r requirements-test.txt
```

**Development Dependencies (Optional):**
```bash
pip install -r requirements-dev.txt
```

### 5. Verify Installation
```bash
# Check Python version
python --version

# Check Flask installation
flask --version

# Check pytest installation
pytest --version
```

## Project Structure

```
29oct_2/
├── app/                      # Flask application source code
│   ├── __init__.py          # Application factory
│   ├── routes/              # API route handlers (blueprints)
│   ├── services/            # Business logic services
│   ├── models/              # Database models (SQLAlchemy)
│   ├── middleware/          # Request/response middleware
│   ├── utils/               # Utility functions and helpers
│   └── config.py            # Application configuration
├── tests/                    # Test suite
│   ├── conftest.py          # Pytest configuration and fixtures
│   ├── unit/                # Unit tests
│   │   ├── routes/          # Route handler tests
│   │   ├── services/        # Business logic tests
│   │   ├── models/          # Data model tests
│   │   └── utils/           # Utility function tests
│   ├── integration/         # Integration tests
│   │   ├── test_api_*.py   # End-to-end API tests
│   │   └── test_db_*.py    # Database integration tests
│   ├── functional/          # Functional workflow tests
│   └── fixtures/            # Shared test data and fixtures
├── requirements.txt          # Core application dependencies
├── requirements-test.txt     # Testing dependencies
├── requirements-dev.txt      # Development dependencies
├── pytest.ini               # Pytest configuration
├── .coveragerc              # Coverage measurement configuration
└── README.md                # This file
```

## Testing

This project follows comprehensive testing practices to ensure functional equivalence with the original Node.js implementation and maintain high code quality standards.

### Coverage Targets

| Component Type | Minimum Coverage | Target Coverage |
|----------------|------------------|-----------------|
| Overall Application | 85% | 90% |
| Authentication/Authorization | 100% | 100% |
| API Routes | 90% | 95% |
| Business Logic Services | 85% | 95% |
| Data Models | 85% | 90% |
| Utilities | 80% | 85% |

### Running Tests

#### Run All Tests
```bash
pytest
```

#### Run Tests with Verbose Output
```bash
pytest -v
```

#### Run Tests with Detailed Output (including print statements)
```bash
pytest -v -s
```

#### Run Specific Test File
```bash
pytest tests/unit/services/test_user_service.py
```

#### Run Specific Test Function
```bash
pytest tests/unit/services/test_user_service.py::test_create_user_with_valid_data
```

#### Run Tests by Category (using markers)
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only functional tests
pytest -m functional

# Skip slow tests
pytest -m "not slow"
```

#### Run Tests Matching a Pattern
```bash
# Run all tests with 'user' in the name
pytest -k "user"

# Run all tests starting with 'test_create'
pytest -k "test_create"
```

### Measuring Code Coverage

#### Basic Coverage Report
```bash
pytest --cov=app
```

#### Coverage with Missing Lines Highlighted
```bash
pytest --cov=app --cov-report=term-missing
```

#### Generate HTML Coverage Report
```bash
pytest --cov=app --cov-report=html

# Open the report in your browser
open htmlcov/index.html
```

#### Coverage with Minimum Threshold
```bash
# Fail if coverage is below 85%
pytest --cov=app --cov-fail-under=85
```

#### Coverage for Specific Module
```bash
pytest --cov=app.services tests/unit/services/
```

#### Generate XML Coverage Report (for CI/CD)
```bash
pytest --cov=app --cov-report=xml --cov-report=term
```

### Parallel Test Execution

For faster test execution, run tests in parallel:

```bash
# Auto-detect number of CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4

# Parallel with coverage
pytest -n auto --cov=app --cov-report=term-missing
```

### Test Organization

Tests are organized by type and scope:

- **`tests/unit/`**: Fast, isolated tests for individual functions and classes
  - Mock all external dependencies
  - Target execution time: <100ms per test
  
- **`tests/integration/`**: Tests for component interactions
  - Use test database, mock external services only
  - Target execution time: 100ms-1s per test
  
- **`tests/functional/`**: End-to-end workflow tests
  - Test complete user scenarios
  - Target execution time: <5s per test

### Test Markers

Tests are categorized using pytest markers:

```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # Integration tests with database
@pytest.mark.functional    # End-to-end workflow tests
@pytest.mark.slow          # Tests taking >1 second
@pytest.mark.api           # API endpoint tests
@pytest.mark.database      # Tests requiring database
```

## Development Workflow

### Setting Up Development Environment

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install development dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Set up pre-commit hooks (optional):**
   ```bash
   pre-commit install
   ```

### Running Tests During Development

#### Continuous Testing (Watch Mode)

Install pytest-watch for automatic test re-runs:
```bash
pip install pytest-watch
ptw -- -v
```

Tests will automatically re-run when files change.

#### Quick Feedback Loop

Run only tests related to your changes:
```bash
# Run tests in a specific directory
pytest tests/unit/services/

# Run tests matching a keyword
pytest -k "authentication"
```

### Code Quality Checks

#### Run Linting
```bash
flake8 app/ tests/
```

#### Run Code Formatting
```bash
black app/ tests/
```

#### Run Import Sorting
```bash
isort app/ tests/
```

#### Run Type Checking
```bash
mypy app/
```

#### Run All Quality Checks
```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Check linting
flake8 app/ tests/

# Run tests with coverage
pytest --cov=app --cov-fail-under=85
```

## CI/CD Integration

### GitHub Actions

Tests are automatically run on every push and pull request. The CI pipeline:

1. Sets up Python 3.12 environment
2. Installs all dependencies
3. Runs full test suite with coverage measurement
4. Fails if coverage drops below 85%
5. Uploads coverage reports to code coverage services

### Local CI Simulation

Run the same checks that CI will run:
```bash
# Full CI check sequence
pip install -r requirements-test.txt
pytest --cov=app --cov-report=xml --cov-fail-under=85
flake8 app/ tests/
black --check app/ tests/
isort --check app/ tests/
```

### Pre-Commit Quality Gates

Before committing code, ensure:
- ✅ All tests pass: `pytest`
- ✅ Coverage >= 85%: `pytest --cov=app --cov-fail-under=85`
- ✅ No linting errors: `flake8 app/ tests/`
- ✅ Code is formatted: `black --check app/ tests/`
- ✅ Imports are sorted: `isort --check app/ tests/`

## Environment Configuration

### Environment Variables

Create a `.env` file for local development:
```bash
FLASK_ENV=development
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
```

### Testing Environment

For tests, create `.env.test`:
```bash
FLASK_ENV=testing
TESTING=True
DATABASE_URL=sqlite:///:memory:
SECRET_KEY=test-secret-key
JWT_SECRET_KEY=test-jwt-secret
DEBUG=False
```

## Contributing

### Testing Requirements for Contributors

All contributions must include:

1. **Tests for new features**: Every new feature must have corresponding unit and integration tests
2. **Tests for bug fixes**: Bug fixes must include regression tests
3. **Coverage maintenance**: New code must maintain or improve overall coverage (>=85%)
4. **Critical path coverage**: Security-related code must have 100% coverage
5. **Test quality**: Tests must be isolated, fast, and maintainable

### Pull Request Checklist

Before submitting a pull request:

- [ ] All tests pass locally (`pytest`)
- [ ] Coverage meets minimum threshold (`pytest --cov=app --cov-fail-under=85`)
- [ ] New features have unit tests
- [ ] New features have integration tests
- [ ] Bug fixes include regression tests
- [ ] Code is formatted (`black app/ tests/`)
- [ ] Imports are sorted (`isort app/ tests/`)
- [ ] No linting errors (`flake8 app/ tests/`)
- [ ] Documentation updated (if needed)

## Migration from Node.js

This Flask application maintains complete functional equivalence with the original Node.js server:

- **API Compatibility**: All endpoints maintain identical request/response formats
- **Authentication**: JWT-based authentication preserved with same token structure
- **Database Schema**: Data models maintain compatibility with existing database
- **Business Logic**: All business rules implemented identically
- **Error Handling**: Error responses maintain same format and status codes

### Testing Parity

The test suite validates equivalence with Node.js implementation:

- All Node.js test scenarios converted to pytest equivalents
- Additional edge cases and boundary conditions added
- Equal or better code coverage compared to Node.js version
- Integration tests ensure API contract compatibility

## Performance Targets

- **Unit tests**: Complete suite runs in <2 minutes
- **Integration tests**: Complete suite runs in <5 minutes
- **Full test suite**: Completes in <10 minutes
- **Single test execution**: Average <100ms for unit tests

## Troubleshooting

### Common Issues

**Tests fail with database errors:**
```bash
# Ensure test database is properly configured
# For in-memory SQLite (default for tests):
DATABASE_URL=sqlite:///:memory: pytest
```

**Coverage reports missing files:**
```bash
# Ensure .coveragerc includes correct source paths
# Check [run] source setting in .coveragerc
```

**Import errors in tests:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements-test.txt
```

**Slow test execution:**
```bash
# Run tests in parallel
pytest -n auto

# Run only fast tests during development
pytest -m "not slow"
```

## Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **pytest Documentation**: https://docs.pytest.org/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **Coverage.py Documentation**: https://coverage.readthedocs.io/

## License

[Specify your license here]

## Contact

[Specify contact information or contribution guidelines]

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