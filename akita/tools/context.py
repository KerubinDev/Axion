import os
from pathlib import Path
from typing import Any, List, Dict, Optional
from pydantic import BaseModel

class FileContext(BaseModel):
    path: str
    content: str
    extension: str
    summary: Optional[str] = None # New field for semantic summary

class ContextSnapshot(BaseModel):
    files: List[FileContext]
    project_structure: List[str]
    rag_snippets: Optional[List[Dict[str, Any]]] = None

class ContextBuilder:
    def __init__(
        self, 
        base_path: str, 
        extensions: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
        max_file_size_kb: int = 50,
        max_files: int = 50,
        use_semantical_context: bool = True
    ):
        self.base_path = Path(base_path)
        self.extensions = extensions or [".py", ".js", ".ts", ".cpp", ".h", ".toml", ".md", ".json"]
        self.exclude_dirs = exclude_dirs or [".git", ".venv", "node_modules", "__pycache__", "dist", "build"]
        self.max_file_size_kb = max_file_size_kb
        self.max_files = max_files
        self.use_semantical_context = use_semantical_context
        
        if self.use_semantical_context:
            try:
                from akita.core.ast_utils import ASTParser
                from akita.core.indexing import CodeIndexer
                self.ast_parser = ASTParser()
                self.indexer = CodeIndexer(str(self.base_path))
            except ImportError:
                self.ast_parser = None
                self.indexer = None

    def build(self, query: Optional[str] = None) -> ContextSnapshot:
        """
        Scan the path and build a context snapshot.
        If a query is provided and indexer is available, it includes RAG snippets.
        """
        files_context = []
        project_structure = []
        rag_snippets = None
        
        if query and self.indexer:
            try:
                # Ensure index exists (lazy indexing for now)
                # In production, we'd have a separate command or check timestamps
                rag_snippets = self.indexer.search(query, n_results=10)
            except Exception:
                pass

        if self.base_path.is_file():
            if self._should_include_file(self.base_path):
                files_context.append(self._read_file(self.base_path))
                project_structure.append(str(self.base_path.name))
        else:
            for root, dirs, files in os.walk(self.base_path):
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                rel_root = os.path.relpath(root, self.base_path)
                if rel_root == ".":
                    rel_root = ""

                for file in files:
                    file_path = Path(root) / file
                    if self._should_include_file(file_path):
                        if len(files_context) < self.max_files:
                            context = self._read_file(file_path)
                            if context:
                                files_context.append(context)
                                project_structure.append(os.path.join(rel_root, file))
        
        return ContextSnapshot(
            files=files_context, 
            project_structure=project_structure,
            rag_snippets=rag_snippets
        )

    def _should_include_file(self, path: Path) -> bool:
        if path.name == ".env" or path.suffix == ".env":
            return False
            
        if path.suffix not in self.extensions:
            return False
        
        if not path.exists():
            return False
            
        # Check size (we can be more lenient if using semantic summaries)
        size_limit = self.max_file_size_kb * 1024
        if self.use_semantical_context:
            size_limit *= 2 # Allow larger files if we can summarize them
            
        if path.stat().st_size > size_limit:
            return False
            
        return True

    def _read_file(self, path: Path) -> Optional[FileContext]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                summary = None
                if self.use_semantical_context and self.ast_parser and path.suffix == ".py":
                    try:
                        defs = self.ast_parser.get_definitions(str(path))
                        if defs:
                            summary_lines = [f"{d['type'].upper()} {d['name']} (L{d['start_line']}-L{d['end_line']})" for d in defs]
                            summary = "\n".join(summary_lines)
                    except Exception:
                        pass

                return FileContext(
                    path=str(path.relative_to(self.base_path) if self.base_path.is_dir() else path.name),
                    content=content,
                    extension=path.suffix,
                    summary=summary
                )
        except Exception:
            return None
