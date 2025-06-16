
# Developer Guidelines

This section of the documentation provides guidelines for developers who want to modify or contribute to the tool.


## Developer Install

1. Clone the project using `git clone https://github.com/bellingcat/auto-archiver.git` 
2. Install uv using `pip install uv` (or see [uv's official documentation](https://github.com/astral-sh/uv))
3. Create virtual environment and install dependencies with `uv venv && source .venv/bin/activate && uv pip install -e .`

## Running 
4. Run the code with `auto-archiver [my args]` (after activating the virtual environment)

```{note}
To activate the virtual environment in any new terminal session:
`source .venv/bin/activate`
This allows you to run the auto-archiver directly without any prefix.
```

### Optional Development Packages

Install development packages (used for unit tests etc.) using:
`uv pip install -e .[dev]`


```{toctree}
:hidden:
creating_modules
docker_development
testing
docs
release
settings_page
style_guide
```