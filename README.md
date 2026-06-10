# Readmegen

![Language](https://img.shields.io/badge/Language-Python-3776ab)

## Table of Contents

- [About](#about)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Scripts](#scripts)
- [Contributing](#contributing)
- [License](#license)

---

## About

AI-powered README generator for public GitHub repositories, providing a clear and compelling project description.

## How It Works

The project uses a combination of natural language processing and machine learning models to analyze the repository context and extract structured information for a README file. It utilizes a decision sequence to pick the right model backend, either Ollama or Groq, and returns a ready-to-use client. The project follows a strict output contract, providing raw JSON output with every field present.

## Teck Stack

- Python 3.11
- Typer
- Rich
- Pathspec
- Pydantic
- Jinja2
- Ollama
- Groq

## Prerequisites

- Python 3.11+
- pip

## Installation

1. Run:

  ```bash
  git clone https://github.com/owner/readmegen
  ```

2. Run:

  ```bash
  cd readmegen
  ```

3. Run:

  ```bash
  pip install .
  ```

4. Run:

  ```bash
  cp .env.example .env
  ```

## Usage

Scan a repository and show results

```bash
readmegen scan <path>
```

Generate a README file for a repository

```bash
readmegen generate <path>
```

## Scripts

| Command | Description |
|---|---|
| `readmegen` | AI-powered README generator |

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](LICENSE)
