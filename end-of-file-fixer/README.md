# end-of-file-fixer

A reusable composite GitHub Action that makes sure the files changed in a pull request end with exactly
one newline. By default it annotates files with a wrong ending and fails the job. With `fix: true`, it
repairs them in the workspace instead.

**Status:** not released yet. The examples below use the `end-of-file-fixer/v1` tag, which doesn't exist
until the first release.

## Usage

Add a workflow to the repository you want to check, for example
`.github/workflows/end-of-file-fixer.yml`:

```yaml
---
name: End of file

on:
  pull_request:

permissions:
  contents: read
  pull-requests: read

jobs:
  end-of-file:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: zahlenhelfer/gh-actions/end-of-file-fixer@end-of-file-fixer/v1
```

The checkout step is required, because the action reads the files from the workspace. It only supports
`pull_request` events, and on any other event it fails with an error rather than passing without having
checked anything.

### Skip generated or vendored files

`exclude` is a Python regular expression, matched anywhere in the path relative to the workspace:

```yaml
- uses: zahlenhelfer/gh-actions/end-of-file-fixer@end-of-file-fixer/v1
  with:
    exclude: '^(vendor/|dist/)|\.min\.js$'
```

### Fix files and commit them back

With `fix: true`, the action only changes the workspace. What happens next is up to your workflow. This
example commits the result to the pull request branch:

```yaml
---
name: End of file

on:
  pull_request:

permissions:
  contents: write
  pull-requests: read

jobs:
  end-of-file:
    # Fork pull requests get a read-only token, so they can't be pushed to.
    if: github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          ref: ${{ github.head_ref }}
      - uses: zahlenhelfer/gh-actions/end-of-file-fixer@end-of-file-fixer/v1
        with:
          fix: true
      - name: Commit fixes
        run: |
          git diff --quiet && exit 0
          git config user.name 'github-actions[bot]'
          git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
          git commit -am 'style: fix end of file'
          git push
```

Commits pushed with the default `GITHUB_TOKEN` don't start new workflow runs, so required checks won't
run on the fix commit.

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `fix` | No | `false` | Set to `true` to repair files in the workspace instead of failing the job. |
| `exclude` | No | empty | Python regular expression. Paths with a match anywhere in them are skipped. |
| `github-token` | No | `github.token` | Token used to list the files changed in the pull request. |

The action has no outputs. To see what was fixed, use `git diff` in a later step.

## The rule

| File ends with | Result |
| --- | --- |
| One newline (`\n` or `\r\n`) | Correct |
| No newline | One is added, using `\r\n` if the file already contains `\r\n` |
| Several newlines | Reduced to one, keeping the line ending type |
| Nothing but newlines | Emptied |
| Empty file | Correct, stays empty |

A file that ends with a lone `\r` gets a `\n` in its place.

## Results

| Case | `fix: false` | `fix: true` |
| --- | --- | --- |
| All files correct | Passes | Passes |
| Wrong ending | `error` annotation, job fails | File repaired, `warning` annotation, job passes |
| Not a `pull_request` event | `error` annotation, job fails | `error` annotation, job fails |
| Invalid `exclude` pattern | `error` annotation, job fails | `error` annotation, job fails, nothing repaired |

## Which files are checked

The action checks every file the pull request adds, modifies or renames, including lines it didn't touch
in those files. It skips:

- Files matching the `exclude` input
- Files removed by the pull request
- Symlinks
- Paths that aren't in the workspace
- Binary files, detected by a NUL byte in the first 8000 bytes. UTF-16 and UTF-32 text counts as binary.

## Requirements and limitations

- **Runner:** needs `bash`, `python3` and `gh`, which are preinstalled on GitHub-hosted Ubuntu runners. A
  self-hosted runner would need them installed first.
- **Permissions:** private repositories need `pull-requests: read`. A `permissions:` block that doesn't
  list it turns that access off.
- **Large pull requests:** GitHub's API returns at most 3000 files, so files beyond that aren't checked.
- **Merge queues:** `merge_group` events aren't supported, because they have no pull request number.

## How it works

The action asks GitHub's API for the files changed in the pull request and passes the list to
`end_of_file.py`, which uses only the Python standard library. The API gives the same list whichever
commit is checked out, so it works with the default merge commit and with the head branch that committing
fixes back requires. Inputs are passed through `env:`, so they can't be executed as shell commands.

## Development

```text
action.yml                  the action
end_of_file.py              the check and fix logic
tests/test_end_of_file.py   unit tests
```

Run the tests from the root of this repository:

```sh
python3 -m unittest discover -s end-of-file-fixer/tests
```

[`ci.yml`](../.github/workflows/ci.yml) runs these tests. On pull requests, it also runs the action
against the real changed files, then against generated files through a stub `gh`. The generated errors show
up as annotations on passing CI runs. That's expected.

## Releasing

Follow the same steps as [`yaml-lint`](../yaml-lint/README.md#releasing), using the `end-of-file-fixer/`
tag prefix.
