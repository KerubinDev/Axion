from pathlib import Path
from akita.tools.diff import DiffApplier

def test_reject_invalid_context(tmp_path):
    """
    Test that a diff with incorrect context lines is rejected.
    """
    # 1. Create a file with known content
    file_path = tmp_path / "test_file.py"
    file_path.write_text("line1\nline2\nline3\n", encoding="utf-8")
    
    # 2. Create a diff that expects 'line2' to be 'line_WRONG'
    # This simulates an LLM hallucinating the context
    diff = """--- val_test.py
+++ val_test.py
@@ -1,3 +1,3 @@
 line1
-line_WRONG
+line_MODIFIED
 line3
"""
    
    # 3. Apply diff - SHOULD FAIL due to strict context check
    # Note: Currently it might fail due to patch mismatch, but we want to ensure
    # our new logic catches it specifically as a context error before application attempts.
    
    # We pass the directory as base_path so relative paths in diff work (we mock them to match tmp_path file)
    # The diff header has val_test.py, so we rename our file or adjust diff. 
    # Let's adjust file to match diff header relative to base.
    
    (tmp_path / "val_test.py").write_text("line1\nline2\nline3\n", encoding="utf-8")
    
    success = DiffApplier.apply_unified_diff(diff, base_path=str(tmp_path))
    
    assert not success, "Diff application should fail when context does not match"
    
    # Verify content was NOT changed
    content = (tmp_path / "val_test.py").read_text(encoding="utf-8")
    assert content == "line1\nline2\nline3\n", "File should not be modified on failure"

def test_dry_run_safety(tmp_path):
    """
    Test that if a patch fails halfway, no files are modified (dry-run logic).
    """
    # 1. Create file
    (tmp_path / "safety.py").write_text("A\nB\nC\n", encoding="utf-8")
    
    # 2. Malformed diff that might parse but fail application
    # Actually, whatthepatch might fail at parse time or apply time.
    # We want to ensure we don't start writing until we know it works.
    
    diff = """--- safety.py
+++ safety.py
@@ -1,3 +1,3 @@
 A
-B
+MODIFIED
 C
@@ -10,10 +10,10 @@
- NON_EXISTENT_BLOCK
+ SHOULD_FAIL
"""
    
    success = DiffApplier.apply_unified_diff(diff, base_path=str(tmp_path))
    assert not success
    
    # Verify file is untouched
    assert (tmp_path / "safety.py").read_text(encoding="utf-8") == "A\nB\nC\n"

def test_contract_enforcement():
    """
    Test that run_solve raises ValueError if model returns invalid content.
    """

