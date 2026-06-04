# Releasing

PyPI publishing for `context-compiler-directive-drafter` follows the same
trusted-publishing pattern as `context-compiler`.

## Workflow

- GitHub release is published
- release workflow validates the repo (`pre-commit`, `pytest`)
- workflow builds sdist + wheel
- workflow publishes to PyPI using GitHub OIDC trusted publishing

The publish workflow is defined in:

- `.github/workflows/publish-pypi.yml`

## Trusted Publishing

The workflow uses:

- `permissions: id-token: write`
- GitHub environment `pypi`
- `pypa/gh-action-pypi-publish@release/v1`

Repository-side setup still required before first real publish:

1. Create the PyPI project `context-compiler-directive-drafter` if needed.
2. In PyPI trusted publishing settings, add this GitHub repository/workflow.
3. In GitHub, keep the `pypi` environment name matching the workflow.

## Notes

- Do not publish directly from local machines.
- Do not upload artifacts manually when trusted publishing is available.
- Validate with `uv build` locally before cutting a release.
