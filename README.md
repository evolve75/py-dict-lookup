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

- Python 3.13+
- Merriam-Webster API keys (free tier available)

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

## Notes

- This project currently targets online lookups only.
- Error handling is designed to give friendly CLI messages for:
  - missing API keys
  - network issues
  - words not found (with suggestions when available)

## License

BSD 2-clause license. See [LICENSE](LICENSE).
