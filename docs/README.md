# VaultTool Documentation

This directory contains comprehensive documentation for VaultTool.

## Core Documentation

- **[Main README](../README.md)** - Getting started, installation, and basic usage
- **[CHANGELOG](../CHANGELOG.md)** - Version history and release notes

## Feature Documentation

### Key Management

- **[GENERATE_KEY_FEATURE.md](GENERATE_KEY_FEATURE.md)** - Comprehensive guide to the `generate-key` command
  - New key creation
  - Key replacement with backup
  - Automatic rekey (key rotation)
  - Use cases and examples
  - Safety features
  - Security best practices

## Release Documentation

- **[RELEASE_v2.0.1.md](RELEASE_v2.0.1.md)** - Release summary for version 2.0.1
  - New features overview
  - Use cases
  - Upgrade instructions
  - Migration guide

## CI/CD and Deployment

### GitHub Actions

- **[GITHUB_ACTIONS_CI.md](GITHUB_ACTIONS_CI.md)** - Continuous Integration workflow
  - Multi-Python version testing
  - Pre-commit hook execution
  - Coverage reporting
  - Workflow configuration

### PyPI Publishing

- **[PYPI_RELEASE_WORKFLOW.md](PYPI_RELEASE_WORKFLOW.md)** - Automated PyPI release workflow
  - GitHub Actions workflow setup
  - Secret configuration (Repository vs Environment)
  - Release process
  - Version management
  - Troubleshooting

## Quick Links

### For Users

- [Getting Started](../README.md#tldr)
- [Installation](../README.md#installation)
- [Configuration](../README.md#configuration)
- [Usage Guide](../README.md#usage)
- [Security Best Practices](../README.md#security-best-practices)

### For Contributors

- [Contributing Guide](../README.md#contributing)
- [Development Setup](../README.md#development-setup)
- [Releasing to PyPI](../README.md#releasing-to-pypi)
- [CI/CD Documentation](GITHUB_ACTIONS_CI.md)
- [Release Workflow](PYPI_RELEASE_WORKFLOW.md)

### For Maintainers

- [Release Workflow Guide](PYPI_RELEASE_WORKFLOW.md)
- [Creating a Release](RELEASE_v2.0.1.md)
- [GitHub Actions Setup](GITHUB_ACTIONS_CI.md)

## Documentation Structure

```
docs/
├── README.md                       # This file - documentation index
├── img/                            # Images and diagrams
│   └── vaulttool_icon.png
├── GENERATE_KEY_FEATURE.md         # generate-key command documentation
├── RELEASE_v2.0.1.md               # Version 2.0.1 release notes
├── GITHUB_ACTIONS_CI.md            # CI workflow documentation
└── PYPI_RELEASE_WORKFLOW.md        # PyPI release workflow
```

## External Resources

- **GitHub Repository**: https://github.com/jifox/vaulttool
- **PyPI Package**: https://pypi.org/project/vaulttool/
- **Issue Tracker**: https://github.com/jifox/vaulttool/issues
- **Discussions**: https://github.com/jifox/vaulttool/discussions

## Getting Help

- **Built-in CLI Help**: Run `vaulttool --help` or `vaulttool <command> --help`
- **Bug Reports**: [Open an issue](https://github.com/jifox/vaulttool/issues)
- **Feature Requests**: [Start a discussion](https://github.com/jifox/vaulttool/discussions)
- **Main Documentation**: See [README.md](../README.md)

---

**Note:** All documentation follows [Markdown formatting standards](https://www.markdownguide.org/basic-syntax/) and is designed to be readable both on GitHub and in any Markdown viewer.
