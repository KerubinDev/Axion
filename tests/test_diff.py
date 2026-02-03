import pytest
import os
from pathlib import Path
from akita.tools.diff import DiffApplier

def test_apply_unified_diff_success(tmp_path):
    # Create a dummy file
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('hello')\n")
    
    # Create a diff
    diff_text = """--- hello.py
+++ hello.py
@@ -1 +1 @@
-print('hello')
+print('hello world')
"""
    
    applier = DiffApplier()
    success = applier.apply_unified_diff(diff_text, base_path=str(tmp_path))
    
    assert success is True
    assert file_path.read_text() == "print('hello world')\n"
    # Verify backup was created and then moved/deleted (logic might vary)
    # Our implementation keeps backups locally during the process.

def test_apply_unified_diff_rollback(tmp_path):
    # Create two files
    file1 = tmp_path / "file1.py"
    file1.write_text("content 1\n")
    
    file2 = tmp_path / "file2.py"
    file2.write_text("content 2\n")
    
    # Create a diff where the second patch fails (incorrect context)
    diff_text = """--- file1.py
+++ file1.py
@@ -1 +1 @@
-content 1
+modified 1
--- file2.py
+++ file2.py
@@ -1 +1 @@
-WRONG CONTENT
+modified 2
"""
    
    applier = DiffApplier()
    success = applier.apply_unified_diff(diff_text, base_path=str(tmp_path))
    
    assert success is False
    # File 1 should have its original content due to rollback
    assert file1.read_text() == "content 1\n"
    assert file2.read_text() == "content 2\n"

def test_apply_new_file(tmp_path):
    diff_text = """--- /dev/null
+++ new_file.py
@@ -0,0 +1 @@
+print('new file')
"""
    applier = DiffApplier()
    success = applier.apply_unified_diff(diff_text, base_path=str(tmp_path))
    
    assert success is True
    new_file = tmp_path / "new_file.py"
    assert new_file.exists()
    assert new_file.read_text() == "print('new file')\n"
