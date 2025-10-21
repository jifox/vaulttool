# GitHub Issue Templates

This directory contains structured issue templates for the VaultTool repository to help contributors provide consistent and complete information.

## Available Templates

### 1. Bug Report (`bug_report.yml`)

Use this template when reporting bugs or unexpected behavior in VaultTool.

**Includes:**
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Error output
- Environment details (VaultTool version, Python version, OS)
- Configuration file
- Additional context

**Labels:** `bug`

### 2. Feature Request (`feature_request.yml`)

Use this template to suggest new features or enhancements.

**Includes:**
- Problem statement
- Proposed solution
- Alternative solutions considered
- Use cases
- Example usage
- Priority level
- Willingness to contribute

**Labels:** `enhancement`

### 3. General Issue (`general_issue.yml`)

Use this template for questions, documentation issues, discussions, or topics that don't fit the other categories.

**Includes:**
- Issue type selection
- Description and context
- Environment details (optional)
- Related documentation references
- Proposed solutions
- Additional information

**Labels:** `question`

## Configuration (`config.yml`)

The `config.yml` file configures the issue template experience:

- **Blank issues disabled**: Forces users to select a template
- **Contact links**: Provides quick access to:
  - Documentation
  - Discussions
  - Security vulnerability reporting

## Template Format

These templates use GitHub's YAML-based form schema, which provides:

- Type-safe input fields
- Required field validation
- Dropdown menus for consistent selections
- Syntax highlighting for code blocks
- Better user experience compared to Markdown templates
- Automatic labeling

## How to Use

When creating a new issue:

1. Click "New Issue" on the Issues page
2. Choose the appropriate template:
   - **Bug Report** - for bugs and errors
   - **Feature Request** - for new features
   - **General Issue** - for questions and discussions
3. Fill out the required fields
4. Submit the issue

## Benefits

- **Consistency**: All issues follow the same structure
- **Completeness**: Required fields ensure necessary information is provided
- **Efficiency**: Maintainers can triage and resolve issues faster
- **Quality**: Better issue reports lead to better solutions

## Customization

To modify templates:

1. Edit the relevant `.yml` file
2. Test the changes in a fork or draft
3. Submit a PR with your improvements

## Resources

- [GitHub Issue Forms Documentation](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [GitHub Issue Template Best Practices](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates)

## Contact

For questions about these templates, please:
- Open a General Issue
- Start a Discussion
- Contact the maintainers

---

**Last Updated:** October 16, 2025  
**Maintainer:** Josef Fuchs (@jifox)
