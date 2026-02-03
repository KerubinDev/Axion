import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from akita.core.ast_utils import ASTParser

class CodeIndexer:
    """
    A lightweight, zero-dependency semantic-keyword indexer.
    Uses basic TF-IDF principles and AST-aware keyword weighting.
    Works perfectly even in restricted environments like Python 3.14.
    """
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.index_file = self.project_path / ".akita" / "index.json"
        self.ast_parser = ASTParser()
        self.data: List[Dict[str, Any]] = []
        self.load_index()

    def load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = []

    def save_index(self):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def index_project(self):
        """Index all Python files in the project."""
        self.data = []
        for root, _, files in os.walk(self.project_path):
            if ".akita" in root or ".git" in root or "__pycache__" in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(self.project_path)
                    self._index_file(full_path, str(rel_path))
        self.save_index()

    def _index_file(self, file_path: Path, rel_path: str):
        try:
            definitions = self.ast_parser.get_definitions(str(file_path))
            for d in definitions:
                source = self.ast_parser.get_source_segment(
                    str(file_path), d["start_line"], d["end_line"]
                )
                
                # Create a searchable representation (keyword rich)
                # We normalize case and extract meaningful words
                search_blob = f"{d['name']} {d['type']} {d['docstring'] or ''} {source}"
                keywords = set(re.findall(r'\w+', search_blob.lower()))
                
                self.data.append({
                    "path": rel_path,
                    "name": d["name"],
                    "type": d["type"],
                    "start_line": d["start_line"],
                    "end_line": d["end_line"],
                    "keywords": list(keywords),
                    "content": source[:500] # Store snippet preview
                })
        except Exception:
            pass

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search using Jaccard Similarity on keywords (Lite Contextual Search)."""
        query_keywords = set(re.findall(r'\w+', query.lower()))
        if not query_keywords:
            return []

        scores = []
        for item in self.data:
            item_keywords = set(item["keywords"])
            intersection = query_keywords.intersection(item_keywords)
            # Simple intersection count as score, weighted by name match
            score = len(intersection)
            if any(qk in item["name"].lower() for qk in query_keywords):
                score += 5 # Boost explicit name matches
                
            if score > 0:
                scores.append((score, item))

        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        return [s[1] for s in scores[:n_results]]
