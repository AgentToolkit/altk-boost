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

### Adding new components into the toolkit

The repository is divided into toolkits that consist of one or more components. This section will describe adding a new toolkit and its components. If adding to an existing toolkit, skip to [Adding components to a toolkit](adding-components-to-a-toolkit).

#### Adding new toolkit

1. Create a new directory in the root (ex: `myawesome-toolkit`)
2. Create a `pyproject.toml` in this directory and be sure to add `toolkit-core` as a dependency
3. Also create a `README.md` in this directory
4. In this directory, will need a module directory as well (ex: `myawesome_toolkit`)
   1. Create a `__init__.py` in this module directory
5. In this module directory, create a `core` directory with `__init__.py` and `toolkit.py`
   1. `toolkit.py` should extend the base classes from `toolkit_core.core.toolkit` for usage by the actual components
6. In the top-level `pyproject.toml` , add your new toolkit in the following places:
   1. `[project] dependencies`
   2. `[tool.uv.sources]`
   3. `[tool.uv.workspace] members`
7. Add a directory with the toolkit name in `tests` for test cases.

#### Adding components to a toolkit

1. Be sure to update the top-level `pyproject.toml` with any required dependencies for your component.
   1. Also, be careful about dependency versions, in general aim for the widest range of applicable versions.
2. Code should be placed in the module directory, with each component in its own directory.
3. Each component should also have its own `README.md` to describe its usage
4. The LLM provider is in `toolkit-core/llm`, please use LLMClient to call LLMs. Refer to its README for more information.
5. A component should have a class that extends the base class defined in `core` along with:
   1. `supported_phases()` that returns `AgentPhase.RUNTIME` and/or `AgentPhase.BUILDTIME` depending on how the component is intended to be used
   2. `_run()` and/or `_build()` depending on the above
6. Add a corresponding test case in the appropriate folder in `tests`.

## Detecting Secrets

CI requires a "no secrets detected check" to pass. If your CI fails, please try the following.

ofcourse, it is better to do the below check before submitting a PR - that way, you don't accidentally commit a secret!

Easy route to detect secrets

`make detect-secrets`

(Make sure you have Make!)

OR


```
uv pip install --upgrade "git+https://github.com/ibm/detect-secrets.git@master#egg=detect-secrets"
```

```
detect-secrets scan --update .secrets.baseline
```


Audit using the following
```
detect-secrets audit .secrets.baseline
```

The above command will start detecting one secret at a time. You could "accept" or "reject" accordingly.
