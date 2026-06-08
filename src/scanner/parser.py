# reads ecosystem-specific dependency files from a repo root and extracts the declared dependencies.

from pathlib import Path
from dataclasses import dataclass, field
import json
import re
import tomllib


# known framework signatures

FRAMEWORK_SIGNATURES: dict[str, str] = {
    # Python web
    "fastapi":       "FastAPI",
    "flask":         "Flask",
    "django":        "Django",
    "starlette":     "Starlette",
    "tornado":       "Tornado",
    "sanic":         "Sanic",
    # Python data / ML
    "torch":         "PyTorch",
    "tensorflow":    "TensorFlow",
    "keras":         "Keras",
    "sklearn":       "scikit-learn",
    "scikit-learn":  "scikit-learn",
    "pandas":        "Pandas",
    "numpy":         "NumPy",
    "transformers":  "HuggingFace Transformers",
    "langchain":     "LangChain",
    # Python task queues / infra
    "celery":        "Celery",
    "sqlalchemy":    "SQLAlchemy",
    "alembic":       "Alembic",
    "pydantic":      "Pydantic",
    # JS / TS frameworks
    "react":         "React",
    "vue":           "Vue",
    "svelte":        "Svelte",
    "next":          "Next.js",
    "nuxt":          "Nuxt",
    "remix":         "Remix",
    "astro":         "Astro",
    # JS backend
    "express":       "Express",
    "fastify":       "Fastify",
    "nestjs":        "NestJS",
    "@nestjs/core":  "NestJS",
    "hono":          "Hono",
    # JS tooling
    "vite":          "Vite",
    "webpack":       "Webpack",
    "tailwindcss":   "Tailwind CSS",
    "prisma":        "Prisma",
    "drizzle-orm":   "Drizzle ORM",
    # Rust
    "actix-web":     "Actix Web",
    "axum":          "Axum",
    "tokio":         "Tokio",
    "serde":         "Serde",
    # Go
    "gin-gonic/gin": "Gin",
    "labstack/echo": "Echo",
    "gofiber/fiber": "Fiber",
    # Ruby
    "rails":         "Ruby on Rails",
    "sinatra":       "Sinatra",
    # Java
    "spring-boot":   "Spring Boot",
    "spring-core":   "Spring",
    "quarkus":       "Quarkus",
}

# Data Models

@dataclass 
class Dependency:
    name: str
    version: str = ""
    is_dev: bool = False

@dataclass
class ParseResult:
    ecosystem: str
    source_file: str
    dependencies: list[Dependency] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    raw_scripts: dict[str, str] = field(default_factory=dict) 

@dataclass
class AllDependencies:
    results: list[ParseResult] = field(default_factory=list)

    @property
    def all_frameworks(self) -> list[str]:
        seen, out = set(), []
        for r in self.results:
            for f in r.frameworks:
                if f not in seen:
                    seen.add(f)
                    out.append(f)
        return out
    
    @property
    def all_dependencies(self) -> list[Dependency]:
        out = []
        for r in self.results:
            out.extend(r.dependencies)
        return out
    
    @property
    def ecosystems(self) -> list[str]:
        return [r.ecosystem for r in self.results]
    

# Main parsing function

def parse(root: Path) -> AllDependencies:
    result = AllDependencies()
    parsers = [
        ("requirements.txt",  _parse_requirements),
        ("pyproject.toml",    _parse_pyproject),
        ("Pipfile",           _parse_pipfile),
        ("package.json",      _parse_package_json),
        ("Cargo.toml",        _parse_cargo),
        ("go.mod",            _parse_go_mod),
        ("Gemfile",           _parse_gemfile),
        ("pom.xml",           _parse_pom),
    ]

    for filename, parser_fn in parsers:
        file_path = root / filename
        if file_path.exists():
            try:
                parsed = parser_fn(file_path)
                if parsed:
                    result.results.append(parsed)
            except Exception:
                pass

    return result

def _parse_requirements(path: Path) -> ParseResult | None:
    # parses requirements.txt
    deps = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or line.startswith("-"):
            continue

        line = line.split("#")[0].strip()

        match = re.match(r"^([A-Za-z0-9_\-\.\[\]]+)\s*([><=!~^]+\s*[\d\w\.\*,]+)?", line)
        if match:
            name = match.group(1).split("[")[0].strip()
            version = (match.group(2) or "").strip()
            deps.append(Dependency(name=name.lower(), version=version))

    if not deps:
        return None
    
    return ParseResult(
        ecosystem="python",
        source_file="requirements.txt",
        dependencies=deps,
        frameworks=_detect_frameworks([d.name for d in deps])
    )
    

def _parse_pyproject(path: Path) -> ParseResult | None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
 
    deps: list[Dependency] = []
 
    # PEP 517 style: [project] dependencies = ["fastapi>=0.100"]
    pep_deps = data.get("project", {}).get("dependencies", [])
    for entry in pep_deps:
        if isinstance(entry, str):
            match = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([><=!~^,\s\d\w\.\*]*)?", entry)
            if match:
                deps.append(Dependency(
                    name=match.group(1).lower(),
                    version=(match.group(2) or "").strip(),
                ))
 
    # Poetry style: [tool.poetry.dependencies]
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    for name, version in poetry_deps.items():
        if name.lower() == "python":
            continue
        if isinstance(version, str):
            deps.append(Dependency(name=name.lower(), version=version))
        elif isinstance(version, dict):
            deps.append(Dependency(name=name.lower(), version=version.get("version", "")))
 
    # Poetry dev deps
    poetry_dev = (
        data.get("tool", {}).get("poetry", {})
            .get("group", {}).get("dev", {}).get("dependencies", {})
    )
    for name, version in poetry_dev.items():
        if isinstance(version, str):
            deps.append(Dependency(name=name.lower(), version=version, is_dev=True))
 
    if not deps:
        return None
 
    return ParseResult(
        ecosystem="Python",
        source_file="pyproject.toml",
        dependencies=deps,
        frameworks=_detect_frameworks([d.name for d in deps]),
    )
 
 
def _parse_pipfile(path: Path) -> ParseResult | None:
    """
    Parses Pipfile (TOML format).
    Reads [packages] and [dev-packages].
    """
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
 
    deps: list[Dependency] = []
 
    for name, version in data.get("packages", {}).items():
        version_str = version if isinstance(version, str) else ""
        deps.append(Dependency(name=name.lower(), version=version_str))
 
    for name, version in data.get("dev-packages", {}).items():
        version_str = version if isinstance(version, str) else ""
        deps.append(Dependency(name=name.lower(), version=version_str, is_dev=True))
 
    if not deps:
        return None
 
    return ParseResult(
        ecosystem="Python",
        source_file="Pipfile",
        dependencies=deps,
        frameworks=_detect_frameworks([d.name for d in deps]),
    )

def _parse_package_json(path: Path) -> ParseResult | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
 
    deps: list[Dependency] = []
 
    for name, version in data.get("dependencies", {}).items():
        deps.append(Dependency(name=name.lower(), version=version))
 
    for name, version in data.get("devDependencies", {}).items():
        deps.append(Dependency(name=name.lower(), version=version, is_dev=True))
 
    scripts = data.get("scripts", {})
 
    return ParseResult(
        ecosystem="Node.js",
        source_file="package.json",
        dependencies=deps,
        frameworks=_detect_frameworks([d.name for d in deps]),
        raw_scripts=scripts,
    )

def _parse_cargo(path: Path) -> ParseResult | None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
 
    deps: list[Dependency] = []
 
    for name, version in data.get("dependencies", {}).items():
        if isinstance(version, str):
            deps.append(Dependency(name=name.lower(), version=version))
        elif isinstance(version, dict):
            deps.append(Dependency(name=name.lower(), version=version.get("version", "")))
 
    for name, version in data.get("dev-dependencies", {}).items():
        if isinstance(version, str):
            deps.append(Dependency(name=name.lower(), version=version, is_dev=True))
 
    if not deps:
        return None
 
    return ParseResult(
        ecosystem="Rust",
        source_file="Cargo.toml",
        dependencies=deps,
        frameworks=_detect_frameworks([d.name for d in deps]),
    )

def _parse_go_mod(path: Path) -> ParseResult | None:
    deps: list[Dependency] = []
    in_require_block = False
 
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
 
        if line == "require (":
            in_require_block = True
            continue
        if in_require_block and line == ")":
            in_require_block = False
            continue
 
        if line.startswith("require "):
            line = line[len("require "):].strip()
 
        if in_require_block or line.startswith("github.com") or line.startswith("golang.org"):
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]
                is_indirect = "// indirect" in line
                deps.append(Dependency(
                    name=name,
                    version=version,
                    is_dev=is_indirect,
                ))
 
    if not deps:
        return None
 
    return ParseResult(
        ecosystem="Go",
        source_file="go.mod",
        dependencies=deps,
        frameworks=_detect_frameworks([d.name for d in deps]),
    )

def _parse_gemfile(path: Path) -> ParseResult | None:
    deps: list[Dependency] = []
 
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
 
        # gem 'rails', '~> 7.0'  or  gem "sinatra"
        match = re.match(r"""gem\s+['"]([^'"]+)['"]\s*(?:,\s*['"]([^'"]+)['"])?""", line)
        if match:
            deps.append(Dependency(
                name=match.group(1).lower(),
                version=match.group(2) or "",
            ))
 
    if not deps:
        return None
 
    return ParseResult(
        ecosystem="Ruby",
        source_file="Gemfile",
        dependencies=deps,
        frameworks=_detect_frameworks([d.name for d in deps]),
    )

def _parse_pom(path: Path) -> ParseResult | None:
    import xml.etree.ElementTree as ET
 
    try:
        tree = ET.parse(path)
    except Exception:
        return None
 
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    root = tree.getroot()
 
    # Strip namespace for simpler querying
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r'\sxmlns="[^"]+"', "", raw)   # remove default namespace
    root = ET.fromstring(raw)
 
    deps: list[Dependency] = []
    for dep in root.findall(".//dependency"):
        artifact = dep.findtext("artifactId") or ""
        version  = dep.findtext("version") or ""
        scope    = dep.findtext("scope") or ""
        if artifact:
            deps.append(Dependency(
                name=artifact.lower(),
                version=version,
                is_dev=scope in ("test", "provided"),
            ))
 
    if not deps:
        return None
 
    return ParseResult(
        ecosystem="Java",
        source_file="pom.xml",
        dependencies=deps,
        frameworks=_detect_frameworks([d.name for d in deps]),
    )


# Framework detection based on known signatures

def _detect_frameworks(dependency_names: list[str]) -> list[str]:
    seen, found = set(), []
    for pkg in dependency_names:
        pkg_lower = pkg.lower()
        for signature, frameworks in FRAMEWORK_SIGNATURES.items():
            if pkg_lower == signature.lower() or pkg_lower.startswith(signature.lower()):
                if frameworks not in seen:
                    seen.add(frameworks)
                    found.append(frameworks)
    return found
