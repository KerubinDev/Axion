import os
import shutil
import pathlib
from pathlib import Path
import whatthepatch
from typing import List, Tuple, Optional, Any

class DiffApplier:
    @staticmethod
    def validate_diff_context(patch: Any, file_content: str) -> bool:
        """
        Strictly validates that the context lines in the patch exist in the file content
        at the expected locations.
        """
        if not patch.changes:
            return True

        file_lines = file_content.splitlines()
        
        # We need to simulate the patch application to check context
        # whatthepatch.apply_diff does this, returning None if context doesn't match
        try:
            result = whatthepatch.apply_diff(patch, file_lines)
            return result is not None
        except Exception:
            return False

    @staticmethod
    def apply_unified_diff(diff_text: str, base_path: str = ".") -> bool:
        """
        Applies a unified diff to files in the base_path.
        Includes PRE-FLIGHT DRY-RUN, strict context checking, and then atomic application.
        """
        try:
            patches = list(whatthepatch.parse_patch(diff_text))
        except Exception as e:
            print(f"❌ ERROR: Failed to parse diff: {e}")
            return False

        if not patches:
            print("❌ ERROR: No valid patches found in the diff text.")
            return False

        base = Path(base_path)
        backup_dir = base / ".akita" / "backups"
        
        # --- PHASE 1: PRE-FLIGHT VALIDATION (DRY RUN) ---
        print("🛡️  Running Structural Guard (Dry Run)...")
        pending_changes: List[Tuple[Path, List[str]]] = []
        
        for patch in patches:
            if not patch.header:
                continue
            
            # Resolve path
            rel_path = patch.header.new_path
            is_new = (patch.header.old_path == "/dev/null")
            is_delete = (patch.header.new_path == "/dev/null")

            if is_new:
                rel_path = patch.header.new_path
            elif is_delete:
                rel_path = patch.header.old_path
            else:
                rel_path = patch.header.new_path or patch.header.old_path

            if not rel_path or rel_path == "/dev/null":
                continue
            
            # Clean up path
            if rel_path.startswith("a/") or rel_path.startswith("b/"):
                rel_path = rel_path[2:]
            
            target_file = (base / rel_path).resolve()
            
            # Check existence scenarios
            if not is_new and not target_file.exists():
                print(f"❌ ERROR: Target file {target_file} does not exist.")
                return False
                
            # Read content
            content = ""
            if target_file.exists():
                try:
                    with open(target_file, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                     print(f"❌ ERROR: Could not verify context for binary/non-utf8 file: {rel_path}")
                     return False
            
            # Strict Context Check & Dry Apply
            if not is_new:
                # This uses whatthepatch's internal context verification
                # If it returns None, it means context mismatch or hunk failure
                new_lines = whatthepatch.apply_diff(patch, content.splitlines())
                if new_lines is None:
                    print(f"❌ ERROR: Context Mismatch in {rel_path}.")
                    print("   The code the AI 'saw' does not match the file on disk.")
                    print("   Action aborted to prevent corruption.")
                    return False
                pending_changes.append((target_file, new_lines))
            elif is_new:
                 # valid new file
                 # reconstruct from patch changes for new file
                 new_lines = []
                 for change in patch.changes:
                     if change.line is not None: 
                        new_lines.append(change.line)
                 pending_changes.append((target_file, new_lines))
            elif is_delete:
                 # We mark for deletion by setting new_lines to None
                 pending_changes.append((target_file, None))

        print("✅ Structural Guard Passed. Applying changes...")

        # --- PHASE 2: ATOMIC APPLICATION ---
        backups: List[Tuple[Path, Path]] = []
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            for target_file, new_lines in pending_changes:
                # 1. Backup
                if target_file.exists():
                    backup_file = backup_dir / f"{target_file.name}.bak"
                    shutil.copy2(target_file, backup_file)
                    backups.append((target_file, backup_file))
                else:
                    backups.append((target_file, None))

                # 2. Write (or delete)
                if new_lines is None: # Delete
                    target_file.unlink()
                else:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(new_lines) + "\n")
            
            print(f"SUCCESS: Applied changes to {len(pending_changes)} files.")
            
            # 3. Post-flight Validation (Tests)
            if (base / "tests").exists():
                print("🧪 Running post-flight validation (pytest)...")
                import subprocess
                result = subprocess.run(["pytest"], cwd=str(base), capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ Validation FAILED:\n{result.stdout}")
                    raise Exception("Post-flight validation failed. Tests are broken.")
                else:
                    print("✅ Post-flight validation passed!")
            
            return True

        except Exception as e:
            print(f"CRITICAL ERROR during write: {e}. Starting rollback...")
            for target, backup in backups:
                if backup and backup.exists():
                    shutil.move(str(backup), str(target))
                elif not backup and target.exists():
                    target.unlink()
            return False

    @staticmethod
    def apply_whole_file(file_path: str, content: str):
        """Safely overwrite or create a file."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
