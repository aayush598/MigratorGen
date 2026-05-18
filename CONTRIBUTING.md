# Contributing to MigratorGen

Thank you for your interest in contributing to MigratorGen! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+ (or use Docker Compose)
- Redis 7+

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/anomalyco/migrator-platform.git
   cd migrator-platform
   ```

2. **Install dependencies**
   ```bash
   make install-dev
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Start infrastructure services**
   ```bash
   make docker-up
   ```

5. **Run database migrations**
   ```bash
   make migrate
   ```

6. **Verify the installation**
   ```bash
   make health
   ```

## Code Style

We use [Ruff](https://beta.ruff.rs/) for linting and formatting.

### Formatting Rules

- Maximum line length: 100 characters
- Use single quotes for strings
- No trailing whitespace
- No unnecessary whitespace

### Running Linters

```bash
# Check for issues
make lint

# Auto-fix issues
make lint-fix

# Format code
make format
```

### Type Checking

We use [mypy](https://mypy-lang.org/) for static type checking.

```bash
make typecheck
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
python -m pytest tests/unit/test_migration.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Use descriptive test names: `test_<function>_<expected_behavior>`
- Follow the AAA pattern: Arrange, Act, Assert
- Mock external dependencies
- Aim for meaningful assertions, not just `assert True`

Example:
```python
def test_transactional_migration_rollback_on_error():
    # Arrange
    engine = TransactionalMigrationEngine()
    migration = create_test_migration()

    # Act & Assert
    with pytest.raises(MigrationError):
        engine.execute(migration, fail_at_step=3)
    assert engine.get_state() == "rolled_back"
```

## Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(api): add batch migration endpoint

fix(worker): prevent duplicate task processing

docs(readme): update installation instructions

test(migration): add tests for rollback functionality
```

## Pull Request Process

### Before Submitting

1. Ensure all tests pass: `make test`
2. Run linters: `make lint`
3. Run type checks: `make typecheck`
4. Update documentation if needed
5. Add tests for new functionality

### PR Description

Include the following in your PR description:

- **Summary**: Brief description of changes
- **Motivation**: Why this change is needed
- **Changes**: Detailed list of changes
- **Testing**: How the changes were tested
- **Screenshots**: If UI changes are involved

### Review Process

1. Automated checks must pass (CI)
2. At least one maintainer approval required
3. Address review feedback
4. Keep commits atomic and well-described

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- MAJOR version for incompatible API changes
- MINOR version for backward-compatible functionality
- PATCH version for backward-compatible bug fixes

### Release Steps

1. Update `CHANGELOG.md` with changes since last release
2. Create git tag: `make release` (enter version when prompted)
3. CI/CD pipeline will:
   - Run all tests
   - Build Docker images
   - Push to GitHub Container Registry
   - Create GitHub release
   - Notify Slack

### Hotfix Process

For critical fixes:

1. Create branch from main: `git checkout -b hotfix/description`
2. Make minimal changes
3. Get expedited review
4. Merge and tag immediately

## Code of Conduct

### Our Pledge

We are committed to making participation in this project a harassment-free experience for everyone.

### Our Standards

- Be respectful and inclusive
- Use welcoming and inclusive language
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Our Responsibilities

Project maintainers are responsible for:
- Clarifying standards of acceptable behavior
- Removing, editing, or rejecting comments, commits, code, etc.
- Temporarily or permanently banning contributors for harmful behavior

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the project team. All complaints will be reviewed and investigated and will result in a response that is deemed necessary and appropriate.

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/anomalyco/migrator-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anomalyco/migrator-platform/discussions)
- **Slack**: Join our community channel

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
