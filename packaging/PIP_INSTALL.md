# Pip install and the wheel

`pyproject.toml` builds an `aureon` wheel and a source distribution. The
installed files are the `aureon` package — trading modules included — and the
inert console module `protected_console_bootstrap_v05`. The frontend, the
appliance tree, and `aureon_fusion` are not in the wheel.

This is source packaging. It is not a supported runtime release. Go-live stays
**HOLD**. The console scripts installed by the wheel (`aureon-operator`,
`aureon-organism`, `aureon-hnc`, `aureon-local-gui`, `aureon-website`) call
that inert module, print a HOLD receipt, and exit 1. They do not start a
listener, import a trading target, or place an order. A checkout launcher can
still stop at the same go-live HOLD.

Importing `aureon` loads the package. That import does not start those scripts.
Other callables in the package remain ordinary Python; the HOLD receipt covers
the installed console scripts and the supported launch path, not every function
in the tree.

The distribution version is **2.1.0**. `aureon.__version__` is a separate
in-module string and is not the wheel version. Read the installed version with
`importlib.metadata.version("aureon")`.

Public PyPI is refused. This repository does not upload there. A TestPyPI
upload exists only as a manual GitHub Actions gate, and it still waits for
Gary's own yes plus a token that is not in the tree.

On 2026-11-05 the project name `aureon` was absent from both indexes. This
change does not register the name. Someone else can still take it before any
later upload.

## Install from git

pip clones the repository, builds a wheel, and installs that wheel. No index
upload is involved.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install 'aureon[operator] @ git+https://github.com/RA-CONSULTING/Aureon-OS.git'
```

Append `@` and a commit SHA when you want a fixed revision:

```bash
python -m pip install 'aureon[operator] @ git+https://github.com/RA-CONSULTING/Aureon-OS.git@bb04503119681adcf832f3c3e9b0cbf09fc7a938'
```

An editable install still needs a checkout:

```bash
git clone https://github.com/RA-CONSULTING/Aureon-OS.git
cd Aureon-OS
python -m pip install -e '.[operator]'
```

The dashboard, `./install.sh`, and the offline pytest path stay on the
checkout. The wheel does not replace them.

## Dry-run build

From a checkout, with Python 3.11 or newer:

```bash
python -m pip install --disable-pip-version-check build==1.6.1 twine==7.0.0
python packaging/build_wheel.py
```

That writes `dist/python-wheel/aureon-2.1.0-py3-none-any.whl` and
`dist/python-wheel/aureon-2.1.0.tar.gz`, checks the metadata, installs the
wheel into a throwaway virtualenv, and runs the five console scripts. Each
script must return HOLD. The script's last line is a JSON report with
`"uploaded": false`. It has no upload option.

`.github/workflows/python-wheel.yml` runs that dry run on pull requests and on
pushes to `main`, and stores the artifacts for seven days. The dry-run job
has no token and does not upload.

## TestPyPI, only behind the gate

Nothing in this pull request uploads. The publish job is skipped unless every
item below is true:

1. Someone runs the **Python wheel** workflow with **Run workflow**.
2. `publish_target` is `testpypi`.
3. `confirm` is the exact string `publish-testpypi`.
4. The repository variable `AUREON_ALLOW_TESTPYPI` is `gary-yes`.
5. The repository secret `TESTPYPI_API_TOKEN` is a TestPyPI API token.
6. The job's GitHub environment is `testpypi`.

Set a required reviewer on the `testpypi` environment before setting the
variable or the secret. GitHub creates that environment the first time the
job is queued. A reviewer added afterwards does not cover the run that
already started.

The upload URL in `packaging/upload_testpypi.py` is fixed to
`https://test.pypi.org/legacy/`. The script refuses any other host, refuses
to run outside GitHub Actions, and refuses a `workflow_dispatch` that missed
a gate. It never reads a public-index token. Do not add one.

After a gated upload of version 2.1.0, install with:

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  'aureon[operator]==2.1.0'
```

The extra index fetches dependencies such as `requests`. It does not upload
this project. Until the gated upload has happened, that command reports that
the project was not found.

Creating the token, setting `AUREON_ALLOW_TESTPYPI`, and saying yes are
Gary's. This tree does not do it.
