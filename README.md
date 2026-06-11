# Scanner I

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

This project is an AI-powered README generator, designed for senior software engineers to analyze a repository context and extract structured information for a README file, targeting public GitHub repositories.

## How It Works

The project utilizes a decision layer that picks the right model backend, either Ollama or Groq, based on the preferred model specified in the config.json file. It then uses the chosen model to generate a README file by analyzing the repository context and extracting relevant information. The project consists of several components, including a scanner, analyzer, and router, which work together to generate the README file. The scanner gathers information about the repository, the analyzer processes this information and generates a context string, and the router decides which model to use. The project also includes a parser that takes the model's output and converts it into a validated AnalysisObject, which is then used to generate the README file.

## Teck Stack

- Python 3.11
- Typer 0.12
- Rich 13
- Pathspec 0.12
- Pydantic 2
- Jinja2 3

## Prerequisites

- Python 3.11+
- pip
- Git

## Installation

1. Run:

  ```bash
  git clone https://github.com/owner/repo
  ```

2. Run:

  ```bash
  cd repo
  ```

3. Run:

  ```bash
  pip install -r requirements.txt
  ```

4. Run:

  ```bash
  cp .env.example .env
  ```

5. Run:

  ```bash
  pip install .
  ```

## Usage

Generate a README file for the current repository

```bash
readmegen
```

Generate a README file for a specific repository

```bash
readmegen --repo https://github.com/owner/repo
```

Generate a README file with a specific model

```bash
readmegen --model groq
```

## Scripts

| Command | Description |
|---|---|
| `readmegen` | Generate a README file for the current repository |

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](LICENSE)
