---
name: release
description: |
	Release clastic to PyPI. Handles version bumping (CalVer YY.MINOR.MICRO),
	tagging, pushing, and post-publish verification. Use when asked to
	"release clastic", "cut a release", "publish to PyPI", or "bump version".
---

# Release clastic

clastic uses CalVer: `YY.MINOR.MICRO` (e.g. `26.0.1`). The version lives in
`clastic/__init__.py` as a `__version__` literal string. During development it
carries a `dev` suffix (e.g. `26.0.1dev`). Flit reads this at build time.

Tags use the `v` prefix (e.g. `v26.0.1`, NOT `26.0.1`). The publish workflow
triggers on tags matching `v[0-9]*.[0-9]*.[0-9]*`.

## Pre-flight checks

Before starting, verify ALL of these:

1. Working tree is clean (`git status` shows nothing dirty/staged)
2. You are on `master` branch
3. `clastic/__init__.py` has a `dev` suffix on `__version__`
4. All tests pass: `pytest clastic/tests/ -v`
5. Check what is actually published on PyPI: https://pypi.org/project/clastic/
	 **PyPI is canonical.** If the intended version already exists on PyPI, it
	 cannot be re-released -- bump to the next version instead. If a local/GitHub
	 tag exists for a version that is NOT on PyPI, the prior release failed and
	 should be retried (see "Failed release" under Error recovery).

If any check fails, stop and report. Do not proceed with a dirty tree or
failing tests.

## Release steps

### 1. Determine the release version

Read `__version__` from `clastic/__init__.py`. Strip the `dev` suffix.
Example: `26.0.1dev` becomes `26.0.1`.

Ask the user to confirm the version. If they want a different version
(e.g. bumping minor instead of micro), use that instead.

### 2. Update version for release

Edit `clastic/__init__.py`: remove the `dev` suffix from `__version__`.

```python
# Before
__version__ = '26.0.1dev'
# After
__version__ = '26.0.1'
```

### 3. Update CHANGELOG.md

Add a new section at the top of `CHANGELOG.md` (below the `# clastic Changelog`
heading) for the release version. Use this format:

```markdown
## 26.0.1

_(Month Day, Year)_

- First change description
- Second change description
```

To determine what changed, review the commits since the last tag:

```bash
git log $(git describe --tags --abbrev=0)..HEAD --pretty=format:'%s' --no-merges
```

Summarize the user-facing changes as concise bullet points. Omit version bump
commits and other release-mechanical commits. Ask the user to confirm or adjust
the changelog entry.

### 4. Commit the release

```bash
git commit -am "clastic version 26.0.1"
```

Use the exact format `clastic version X.Y.Z` for the commit message.

### 5. Tag the release

```bash
git tag -a v26.0.1 -m "short summary of key changes in this release"
```

Tags use the `v` prefix. The tag message should be a short,
lowercase, descriptive summary of the release (not just the version number).
Examples:

- `"migrate to flit, expand test coverage, add CI"`
- `"python 3.10-3.14 support, windows fixes"`
- `"modernize build system, drop python 3.8/3.9"`

### 6. Bump to next dev version

Increment the micro version and add `dev` suffix:

```python
__version__ = '26.0.2dev'
```

### 7. Commit the dev bump

```bash
git commit -am "bump version to 26.0.2dev"
```

### 8. Push

```bash
git push origin master --tags
```

This triggers two GitHub Actions workflows:
- `Tests` (on the push to master)
- `Publish to PyPI` (on the tag)

The publish workflow validates that `__version__` on the tagged commit does
not contain `dev` and matches the tag (after stripping the `v` prefix). It
parses `__version__` from the file with `sed` rather than importing the module
(the build job does not install dependencies). If either check fails,
publishing is blocked.

## Post-publish verification

After pushing, wait ~2 minutes for PyPI propagation, then verify in a
temporary virtualenv **outside the repo** (to avoid the local source tree
shadowing the installed package):

```bash
python3 -m venv /tmp/clastic-verify && source /tmp/clastic-verify/bin/activate
uv pip install --system pytest chameleon Mako psutil
pip install clastic==26.0.1 --index-url https://pypi.org/simple/
cd /tmp  # MUST leave repo root so local clastic/ does not shadow the install
python -c "import clastic; print(clastic.__version__)"
# Should print: 26.0.1
deactivate && rm -rf /tmp/clastic-verify
```

If `--index-url` fails with 404, wait another minute and retry. PyPI CDN
propagation can take 1-5 minutes.

Report the results to the user.

## Error recovery

- **Failed release** (tag exists locally/on GitHub but not on PyPI): PyPI is
	the source of truth. Delete the stale tag locally and on the remote:
	```bash
	git tag -d vX.Y.Z
	git push origin :refs/tags/vX.Y.Z  # if it was pushed
	```
	Then check `__version__` in `clastic/__init__.py`. If it was already bumped
	past the failed release (e.g. `X.Y.(Z+1)dev`), reset it to `X.Y.Zdev` so
	the release flow strips the suffix to the correct version. Amend or revert
	the bump commit as needed, then restart the release from step 1.
- **Wrong version tagged**: `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z`
	then fix and re-tag.
- **Publish workflow failed**: Check the GitHub Actions log. Common causes:
	version mismatch, dev suffix present, PyPI trusted publisher not configured.
- **Tests fail after publish**: The package is already on PyPI. File an issue,
	fix forward with a patch release.
