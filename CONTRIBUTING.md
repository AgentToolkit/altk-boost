## How to contribute to Agent Lifecycle Toolkit (ALTK)

Our project welcomes external contributions of all sorts, including:

### Did you find a bug?

* Please file an [issue](https://github.com/AgentToolkit/agent-lifecycle-toolkit/issues).

### Types of contributions:

* Fixing bugs
* Improving existing components in the toolkit.
* Adding new components to the toolkit.

### Setting up for development:

We use [uv](https://docs.astral.sh/uv/) as package and project manager. To install, please check the following documentation page [Installing uv](https://docs.astral.sh/uv/getting-started/installation/).


#### Create a virtual environment
You can use `uv sync` to create a virtual environment (if it doesn't already exist) and install all the project's dependencies in that environment:
```bash
uv venv
```

#### Using a specific python version
If you want to use a specific version of python, then you can create a virtual environment first and then run the sync command as follows:

```bash
uv venv --python 3.12
uv sync
```

For more details refer to the [documentation](https://docs.astral.sh/uv/concepts/python-versions/) on python versions for `uv`.

#### Adding a new dependency
While developing you may want to add a new depdendency. Use `uv add` to automatically update the `pyproject.toml` dependencies and the `uv.lock` file:

```bash
uv add <package_name>
```

The option to use `uv pip install` is there, but please be aware that this doesn't automatically update the `pyproject.toml` dependencies nor the `uv.lock` file. That will have to be done manually. Please refer to the [documentation](https://docs.astral.sh/uv/concepts/projects/dependencies/#adding-dependencies) for more details.

### Coding style guidelines

We use [pre-commit](https://pre-commit.com) for making sure the codebase remains consistent across commits and PRs. The checks will handle linting, formatting, type checks and some other minor enhancements.

Ensure it is installed (preferred):
```bash
pre-commit install
```

Or run it manually:
```bash
pre-commit run --all-files
```

### Adding new components to a lifecycle stage

The `altk` module is divided into lifecycle stages of an agent's exeuction. Each lifecycle stage has a set of components that are designed to be reusable building blocks for solving common problems in that lifecycle stage. This section will describe adding a new component to a lifecycle stage.

1. Determine which lifecycle stage your component belongs. Ask yourself what problem it solves and where it's likely to be most useful for an agent.
1. Once you've selected a lifecycle stage, create a new package under the associated lifecycle package in the `altk` folder.
1. Ensure the `pyproject.toml` is updated with new dependencies and that the `uv.lock` file is up to date.
1. Each component should also have its own `README.md` to outline 3 main things:
   * When to use the component
   * How to use the component
   * Proof (benchmarks, tests, etc.) that the approach works better compared to some baseline performance on the task
1. If your component makes use of LLMs, please use the LLM provider in `altk/core/llm`. You can refer to the [README.md](altk/core/llm/README.md) for more details.
1. A component should have a class that extends the [ComponentBase](altk/core/toolkit.py#L48) class defined in `core` along with the following:
   * `supported_phases()` that returns `AgentPhase.RUNTIME` and/or `AgentPhase.BUILDTIME` depending on how the component is intended to be used.
   * `_run()` if your agent supports the `AgentPhase.RUNTIME` phase.
   * `_build()` if your agent supports the `AgentPhase.BUILDTIME` phase.
1. The component should be accompanied by a set of tests demonstrating that it works. Tests should be placed alongside the `tests` folder.

## Detecting Secrets

We don't want secrets to be leaked so we the CI requires a "no secrets detected check" to pass. If your CI check fails, please try the following. If you run the `pre-commit` checks then this would be detected before the CI has a chance to fail.

Easy route to detect secrets

```bash
make detect-secrets
```

If you have `make` then you can make use of the existing utility to scan for secrets.

Alternatively,


```bash
uv pip install --upgrade "git+https://github.com/ibm/detect-secrets.git@master#egg=detect-secrets"
```

```bash
detect-secrets scan --update .secrets.baseline
```

Audit using the following
```bash
detect-secrets audit .secrets.baseline
```

The above command will start detecting one secret at a time. You will be prompted to "accept" or "reject" detections accordingly.

## Developer Certificate of Origin (DCO)

The Developer Certificate of Origin (DCO) is a per-commit sign-off made by a contributor stating that they agree to the terms published at https://developercertificate.org/ for that particular contribution.

To be DCO compliant, ensure each commit that you contribute is signed off. This can be done by adding the `-s` option when making a commit. For example:

```bash
git commit -s -m <msg>
```

The sign-off will be stored as part of the commit message itself as a line of the format:

```txt
Signed-off-by: Full Name <email>
```
