'''
decides which files to keep and which are supposed o be skipped.
2 layers of filtering logic being used here-

    1. Hard ignore list: list of frameworks, files...etc we always skip
    2. .gitignore rules: loaded from the repo.
'''

from pathlib import Path
import pathspec

# loading the config.json file which contains the hard ignore list

from ..utils.config import get as _get_config
_CFG = _get_config("ignore")

IGNORED_DIRS: set[str] = set(_CFG["directories"])
IGNORED_EXTENSIONS: set[str] = set(_CFG["extensions"])
IGNORED_FILENAMES: set[str] = set(_CFG["filenames"])

# Public API

class FileFilter:
    """
    it is a stateful filter that holds the.gitignore spec for a given repo
    creates one instance per scan, then calls .should_ignore(path) for each file.
    """

    def __init__(self, root: Path):
        self.root = root
        self.gitignore_spec = self._load_gitignore(root)

    # Main section checking function

    def should_ignore(self, path: Path) -> tuple[bool, str]:


        # 1. Skips parent directory if its in the hard ignore list (handles globs like *.egg-info)
        for parent in path.parts:
            if parent in IGNORED_DIRS:
                return True, f"ignored directory: {parent}"
        
        # 2. Skip by filename
        if path.name in IGNORED_FILENAMES:
            return True, f"ignored filename: {path.name}"
        
        # 3. Skip by extension; handles compound extensions like .min.js -> check suffix chain
        suffixes = "".join(path.suffixes)
        if suffixes in IGNORED_EXTENSIONS or path.suffix in IGNORED_EXTENSIONS:
            return True, f"ignored extension: {path.suffix}"
        
        # 4. Skip if matches the .gitignore rules
        if self.gitignore_spec:
            relative = path.relative_to(self.root)
            if self.gitignore_spec.match_file(str(relative)):
                return True, ".gitignore match"
            
        return False, ""
    
    # Internal helper to load .gitignore and create a pathspec matcher

    @staticmethod
    def _load_gitignore(root: Path) -> pathspec.PathSpec | None:
        gitignore_path = root / ".gitignore"
        if not gitignore_path.exists():
            return None
        
        lines = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", lines)
    