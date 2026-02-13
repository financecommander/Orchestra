# Repository Setup Instructions

## 1. Enable Features
- **Issues**: Settings → General → Features → ✅ Issues
- **Projects**: Settings → General → Features → ✅ Projects
- **Discussions**: Settings → General → Features → ✅ Discussions

## 2. Branch Protection Rules for `main`
Settings → Branches → Add rule for `main`:
- ✅ Require pull request reviews before merging (1 approver)
- ✅ Require status checks to pass before merging (CI workflow)
- ✅ Require branches to be up to date before merging
- ❌ Do not allow force pushes

## 3. Secrets
Settings → Secrets and variables → Actions → New repository secret:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `XAI_API_KEY`
- `CODECOV_TOKEN` (optional)

## 4. Labels
Issues → Labels → New label:
| Label               | Color     |
|---------------------|-----------|
| orchestra-workflow  | `#0E8A16` |
| orchestra-escalated | `#D93F0B` |
| P0                  | `#B60205` |
| P1                  | `#D93F0B` |
| P2                  | `#FBCA04` |
| P3                  | `#0E8A16` |
