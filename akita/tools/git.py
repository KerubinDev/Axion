import os
import pathlib
import subprocess
from typing import Tuple, Optional
from urllib.parse import urlparse
from akita.core.config import CONFIG_DIR

class GitTool:
    """
    Utility for managing Git repositories within the Akita ecosystem.
    """
    REPOS_DIR = CONFIG_DIR / "repos"

    @staticmethod
    def parse_repo_url(url: str) -> Tuple[str, str]:
        """
        Extracts owner and repo name from a git URL.
        Supports HTTPS and SSH formats.
        """
        # Clean URL
        clean_url = url.strip().rstrip("/")
        if clean_url.endswith(".git"):
            clean_url = clean_url[:-4]

        host = None
        path_part = None

        # Handle SCP-like SSH syntax: git@github.com:owner/repo
        if "@" in clean_url and ":" in clean_url.split("@", 1)[1]:
            user_host, path_part = clean_url.split("@", 1)[1].split(":", 1)
            host = user_host
        else:
            parsed = urlparse(clean_url)
            host = parsed.hostname
            path_part = parsed.path.lstrip("/") if parsed.path else ""

        if host and (host == "github.com" or host.endswith(".github.com")):
            parts = [p for p in path_part.split("/") if p]
            if len(parts) >= 2:
                return parts[0], parts[1]
        
        # Fallback for other providers or generic paths
        parts = clean_url.split("/")
        if len(parts) >= 2:
            return parts[-2], parts[-1]
            
        raise ValueError(f"Could not parse repository owner and name from URL: {url}")

    @classmethod
    def clone_repo(cls, url: str, branch: Optional[str] = None, depth: Optional[int] = None) -> str:
        """
        Clones a repository to ~/.akita/repos/<owner>/<repo>.
        Returns the local path.
        """
        owner, repo = cls.parse_repo_url(url)
        target_path = cls.REPOS_DIR / owner / repo
        
        if target_path.exists():
            raise FileExistsError(f"Repository already exists at: {target_path}. Please delete it first if you want to re-clone.")
            
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = ["git", "clone"]
        if branch:
            cmd += ["--branch", branch]
        if depth:
            cmd += ["--depth", str(depth)]
            
        cmd += [url, str(target_path)]
        
        result = subprocess.run(cmd, capture_all=True if hasattr(subprocess, 'capture_all') else False, text=True, check=False)
        
        if result.returncode != 0:
            # Clean up parent if it was empty
            if not any(target_path.parent.iterdir()):
                target_path.parent.rmdir()
            raise RuntimeError(f"Git clone failed: {result.stderr or 'Unknown error'}")
            
        return str(target_path)
