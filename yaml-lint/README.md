# yaml-lint

A reusable composite GitHub Action that lints YAML files with
[yamllint](https://yamllint.readthedocs.io/) and reports the findings as annotations on the
affected files. Every repository gets the same shared rules, and a repository can override them.

- **Errors** are annotated and fail the job.
- **Warnings** are annotated and do not fail the job.
- **If yamllint itself fails** (for example, a missing directory or a broken config), the job fails and
  the details are in the step log.

## Usage

Add a workflow to the repository you want to lint, for example `.github/workflows/yaml-lint.yml`:

```yaml
---
name: YAML lint

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  yaml-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: zahlenhelfer/gh-actions/yaml-lint@yaml-lint/v1
```

The checkout step is required, because the action lints the files in the workspace and doesn't fetch
them itself.

### Lint one directory with a specific config

```yaml
- uses: zahlenhelfer/gh-actions/yaml-lint@yaml-lint/v1
  with:
    directory: deploy/
    config: .github/yamllint.yml
```

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `directory` | No | `.` | File or directory to lint, relative to the workspace. Only one path is supported. |
| `config` | No | empty | Path to a yamllint config file. See [Configuration](#configuration). |

The action has no outputs. The result is the annotations and the job status.

## Results

| yamllint result | Exit code | Annotations | Job |
| --- | --- | --- | --- |
| No findings | 0 | None | Passes |
| Warnings only | 0 | `warning` | Passes |
| At least one error | 1 | `error` and `warning` | Fails |
| yamllint failed | 1 or 255 in testing | None from yamllint; details in the log | Fails |

To fail on warnings too, change the rule's level to `error` in your config. The action has no strict
mode input.

GitHub may not display every annotation when a run has many findings. All findings are always in the
step log.

## Configuration

The action uses the first of these it finds:

1. The file given in the `config` input
2. `.yamllint`, `.yamllint.yaml` or `.yamllint.yml` in the working directory or a parent directory
3. The shared rules in [`default-config.yml`](default-config.yml)

The shared rules are yamllint's `default` set, with lines allowed up to 120 characters and the `truthy`
check turned off for keys, so `on:` in workflow files is accepted.

### Overriding the shared rules

Add a `.yamllint.yml` to the root of the repository. **It replaces the shared rules rather than adding
to them**, so copy any shared settings you want to keep:

```yaml
---
extends: default
rules:
  line-length:
    max: 160
  truthy:
    check-keys: false
```

To skip files such as vendored or generated YAML, add `ignore` or `ignore-from-file` to that config. By
default, yamllint lints `*.yaml`, `*.yml` and `.yamllint` files. Run `yamllint --list-files .` to see
exactly what it picks up.

## Requirements and limitations

- **Runner:** needs `bash` and `pipx`. The action targets GitHub-hosted Ubuntu runners. A self-hosted
  runner would need `pipx` installed first.
- **Network:** `pipx` downloads yamllint from PyPI on each run.
- **Single path:** `directory` takes one path, not a list.
- **Unusual file names:** yamllint doesn't escape file names in annotations, so an annotation for a file
  with `,` or `%` in its name may point to the wrong file. The finding is still in the log.
- **Annotation text:** annotations include the position and rule, for example
  `1:5 [trailing-spaces] trailing spaces`.

## How it works

The action has a single step. It sets `$YAMLLINT_CONFIG_FILE` to the shared config, which yamllint only
uses when the repository has no config of its own. It then runs a pinned yamllint through `pipx run`
with `--format github`, which produces the annotations. Inputs are passed through `env:` and quoted, so
they can't be executed as shell commands.

## Development

```text
action.yml               the action
default-config.yml       the shared rules
tests/fixtures/          YAML files with known results, ignored when linting this repository
tests/relaxed-config.yml config for testing the config input
```

Lint this repository from its root:

```sh
yamllint .
```

It has to be the root, because the root `.yamllint.yml` extends `yaml-lint/default-config.yml` by a path
relative to the working directory. Running it from a subdirectory crashes with `FileNotFoundError`.

[`ci.yml`](../.github/workflows/ci.yml) lints this repository with the action and checks its behavior
against the fixtures. The fixture errors and warnings show up as annotations on passing CI runs. That's
expected.

### Updating yamllint

The version is pinned in `action.yml`. Change it there, let CI run, then release. A new yamllint version
can change results, so treat new rules or changed defaults as a breaking change.

## Releasing

This repository holds several shared actions, and git tags apply to the whole repository, so each
action gets its own tag prefix:

- `yaml-lint/v1.0.0` is an exact release and never moves.
- `yaml-lint/v1` is a floating tag that moves to the latest compatible `v1.x.y` release.

Changes on `main` don't reach consumers until a tag moves. Consumers should use the floating tag, or a
commit SHA for the strongest guarantee.

```sh
git tag yaml-lint/v1.0.0
git tag -f yaml-lint/v1
git push origin yaml-lint/v1.0.0
git push -f origin yaml-lint/v1
```

Use a new major version for changes that can fail a previously passing repository, such as stricter
shared rules or a yamllint update with new defaults.

**Not yet confirmed in a workflow:** the GitHub API resolves slash-style tags, but no workflow has used
one in a `uses:` reference yet. If it fails with a resolve or download error, switch to `yaml-lint-v1`
and update this README.
