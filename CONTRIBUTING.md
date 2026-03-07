# Contributing to StarStream

Thank you for your interest in contributing to StarStream!

## Development Setup

```bash
git clone https://github.com/renatocaliari/starstream.git
cd starstream

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all packages
pip install -e packages/starstream[dev]
pip install -e packages/starstream-pocketbase[dev]
pip install -e packages/starstream-loro[dev]
```

## Making Changes

1. **Fork the repo** and create your branch from `main`
2. **Install pre-commit hooks**: `pre-commit install`
3. **Make your changes** with clear commit messages
4. **Add tests** for any new functionality
5. **Run the test suite**: `pytest packages/*/tests -v`
6. **Update documentation** as needed

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to public APIs
- Run `ruff check .` before committing

## Testing

```bash
# Run all tests
pytest packages/*/tests -v

# Run tests for specific package
pytest packages/starstream/tests -v

# Run with coverage
pytest packages/starstream/tests --cov=starstream
```

## Publishing

Releases are handled by maintainers:

```bash
# Version bump (maintainers only)
cd packages/starstream
hatch version minor  # or patch/major

# Build and publish (maintainers only)
hatch build
hatch publish
```

## Questions?

Open an issue or discussion on GitHub!
