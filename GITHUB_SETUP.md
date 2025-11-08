# GitHub Repository Setup

This guide helps you set up the GitHub repository and create the necessary issue for the deferred hanging tests.

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (e.g., `learnr`)
3. **Do NOT initialize** with README, .gitignore, or license (we already have these)

## Step 2: Add Remote and Push

```bash
# Add GitHub as remote (replace with your repository URL)
git remote add origin https://github.com/YOUR_USERNAME/learnr.git

# Push all commits and set upstream
git push -u origin main
```

## Step 3: Create Issue for Hanging Tests

Once your repository is pushed to GitHub, you can create the issue using the GitHub CLI:

```bash
# Create the issue using the template
gh issue create \
  --title "[BUG] 8 Tests Hang Due to Timezone-Aware/Naive DateTime Mismatch" \
  --body-file .github/ISSUE_TEMPLATE/timezone-hanging-tests.md \
  --label "bug,database,tests,priority-medium"
```

**Alternative:** Create the issue manually via GitHub web interface:
1. Go to your repository on GitHub
2. Click "Issues" → "New Issue"
3. Select the template: "Fix Timezone-Aware DateTime Comparison (8 Hanging Tests)"
4. Review and submit

## Step 4: Verify Repository Status

```bash
# Check that remote is configured
git remote -v

# Verify latest commits
git log --oneline -5

# Check branch status
git status
```

## Current Repository State

Your local repository contains:
- ✅ **4 commits:**
  - Initial commit
  - feat: modernize codebase - fix all deprecation warnings
  - docs: add comprehensive project documentation
  - chore: add GitHub issue template for timezone hanging tests

- ✅ **92 application files** (app/, tests/, scripts/)
- ✅ **15 documentation files** (guides, references)
- ✅ **1 GitHub issue template** (timezone hanging tests)

## What Happens Next

After pushing and creating the issue:

1. **Issue will track** the 8 deferred hanging tests
2. **Full documentation** is available in `docs/KNOWN_ISSUES.md`
3. **Migration checklist** is provided in the issue template
4. **Solution path** is clearly defined (Alembic migration to TIMESTAMPTZ)

## Additional GitHub Setup (Optional)

### Enable GitHub Actions for CI/CD

Create `.github/workflows/tests.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --deselect=tests/integration/test_reviews_endpoints.py::TestGetDueReviews --deselect=tests/integration/test_dashboard_endpoints.py::TestGetRecentActivity --deselect=tests/integration/test_diagnostic_endpoints.py::TestGetDiagnosticResults --deselect=tests/integration/test_practice_endpoints.py::TestGetPracticeSession --deselect=tests/integration/test_practice_endpoints.py::TestCompletePracticeSession --deselect=tests/e2e/test_user_journey.py::TestDiagnosticToReviewJourney --deselect=tests/e2e/test_user_journey.py::TestMultiSessionProgressJourney
```

### Set Branch Protection Rules

1. Go to Settings → Branches
2. Add rule for `main` branch:
   - Require pull request reviews
   - Require status checks to pass (tests)
   - Require branches to be up to date

## Need Help?

- **GitHub CLI Installation:** https://cli.github.com/
- **GitHub Docs:** https://docs.github.com/
- **Issue Tracking Best Practices:** https://docs.github.com/en/issues
