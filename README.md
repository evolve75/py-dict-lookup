# py-dict-lookup

A simple Python CLI tool to look up word definitions and synonyms from the command line.

The current implementation uses the [Merriam-Webster APIs][mw] for:
- the Collegiate Dictionary (definitions)
- the Collegiate Thesaurus (synonyms)

[mw]: https://dictionaryapi.com/

## Features

- Look up dictionary definitions from the terminal
- Look up synonyms with a configurable limit
- Clean, readable CLI output
- Uses modern Python tooling (`uv`, `pyproject.toml`)
- Designed for extension (additional providers, caching, etc.)

## Requirements

- Python 3.12+
- Merriam-Webster API keys (free tier available)

## Installation (end users)

You can install `py-dict-lookup` as an isolated CLI tool with either **pipx** or **uv tool**.

### Option 1: pipx

Install:

```bash
pipx install py-dict-lookup
```

Upgrade later:

```bash
pipx upgrade py-dict-lookup
```

### Option 2: uv

```bash
uv tool install py-dict-lookup
```

Upgrade later:

```bash
uv tool upgrade py-dict-lookup
```

### Run:

```bash
py-dict-lookup --help
```

### Configuration (API Keys)

Create a .env file in your current directory (or export the env vars in your shell):

```bash
MW_COLLEGIATE_KEY=your_collegiate_key_here
MW_THESAURUS_KEY=your_thesaurus_key_here
```

You can obtain keys from Merriam-Webster: <https://dictionaryapi.com/>.

### Install directly from GitHub

You can install the CLI directly from the GitHub repository without publishing to PyPI.

Using `pipx`:

```bash
pipx install git+https://github.com/evolve75/py-dict-lookup.git
```

Using `uv`:

```bash
uv tool install git+https://github.com/evolve75/py-dict-lookup.git
```

> Tip: You can also install a specific branch, tag, or commit:

```bash
pipx install git+https://github.com/evolve75/py-dict-lookup.git@main
uv tool install git+https://github.com/evolve75/py-dict-lookup.git@v0.1.0
```

## Installation (development)

Clone the repository and install dependencies using `uv`:

```bash
uv sync
```

You do not need to install the package globally to use it during development.

## Configuration

Create a `.env` file in the project root with your API keys:

```bash
MW_COLLEGIATE_KEY=your_collegiate_key_here
MW_THESAURUS_KEY=your_thesaurus_key_here
```

These keys can be obtained from: <https://dictionaryapi.com/>

## Usage

Run the CLI via `uv run`:

### Show help

```bash
uv run py-dict-lookup --help
```

## JSON output
Use `--json` to emit machine-readable JSON.

Important: `--json` is a **global option**, so it must come **before** the subcommand:

```bash
uv run py-dict-lookup --json define serendipity
uv run py-dict-lookup --json synonyms fast --limit 5
uv run py-dict-lookup --json lookup serendipity --limit 10
```

### Lookup a definition

```bash
uv run py-dict-lookup define <word>
```

### Lookup synonyms

```bash
uv run py-dict-lookup synonyms serendipity  # as an example
```

### Limit the number of synonyms returned

```bash
uv run py-dict-lookup synonyms serendipity --limit 5
```

### Lookup both the definition and the synonyms

```bash
uv run py-dict-lookup lookup serendipity
```

You can also use the short aliases:

```bash
uv run py-dict-lookup d serendipity
uv run py-dict-lookup s serendipity -n 5
uv run py-dict-lookup l serendipity -n 10
```

## Providers

The tool supports multiple dictionary providers via a pluggable provider
architecture.

### Default provider

The default provider is:

- `mw`: Merriam-Webster (Collegiate Dictionary + Thesaurus)

### List available providers

```bash
uv run py-dict-lookup providers
```
## Exit codes

`py-dict-lookup` uses predictable exit codes so it can be safely scripted:

- **0** — Success
- **2** — Word not found (includes suggestions when available)
- **3** — Provider error (network/API/unknown provider, etc.)
- **4** — Configuration error (missing required API key / config)

Examples:

```bash
py-dict-lookup define serendipity
echo $?  # 0

py-dict-lookup define asdfasdfasdf
echo $?  # 2

py-dict-lookup --provider nope define test
echo $?  # 3

# Missing keys
py-dict-lookup define test
echo $?  # 4
```

When using `--json`, errors are still returned with the same exit codes,
and the response includes an "error" field (and "suggestions" for not-found cases).

## Notes

- This project currently targets online lookups only.
- Error handling is designed to give friendly CLI messages for:
  - missing API keys
  - network issues
  - words not found (with suggestions when available)

## License

BSD 2-clause license. See [LICENSE](LICENSE).
