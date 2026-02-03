import os
import shutil
import pathlib
from pathlib import Path
import whatthepatch
from typing import List, Tuple, Optional

class DiffApplier:
    @staticmethod
    def apply_unified_diff(diff_text: str, base_path: str = ".") -> bool:
        """
        Applies a unified diff to files in the base_path.
        Includes backup and rollback logic for atomicity.
        """
        patches = list(whatthepatch.parse_patch(diff_text))
        if not patches:
            print("ERROR: No valid patches found in the diff text.")
            return False

        backups: List[Tuple[Path, Path]] = []
        base = Path(base_path)
        backup_dir = base / ".akita" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            for patch in patches:
                if not patch.header:
                    continue
                
                # whatthepatch identifies the target file in the header
                # We usually want the 'new' filename (the +++ part)
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
                
                # Clean up path (sometimes they have a/ or b/ prefixes)
                if rel_path.startswith("a/") or rel_path.startswith("b/"):
                    rel_path = rel_path[2:]
                
                target_file = (base / rel_path).resolve()
                
                if not is_new and not target_file.exists():
                    print(f"ERROR: Target file {target_file} does not exist for patching.")
                    return False

                # 1. Create backup
                if target_file.exists():
                    backup_file = backup_dir / f"{target_file.name}.bak"
                    shutil.copy2(target_file, backup_file)
                    backups.append((target_file, backup_file))
                else:
                    backups.append((target_file, None)) # Mark for deletion on rollback if it's a new file

                # 2. Apply patch
                content = ""
                if target_file.exists():
                    with open(target_file, "r", encoding="utf-8") as f:
                        content = f.read()
                
                lines = content.splitlines()
                # whatthepatch apply_diff returns a generator of lines
                patched_lines = whatthepatch.apply_diff(patch, lines)
                
                if patched_lines is None:
                    print(f"ERROR: Failed to apply patch to {rel_path}.")
                    raise Exception(f"Patch failure on {rel_path}")

                # 3. Write new content
                target_file.parent.mkdir(parents=True, exist_ok=True)
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(patched_lines) + "\n")

            print(f"SUCCESS: Applied {len(patches)} patches successfully.")
            return True

        except Exception as e:
            print(f"CRITICAL ERROR: {e}. Starting rollback...")
            for target, backup in backups:
                if backup and backup.exists():
                    shutil.move(str(backup), str(target))
                elif not backup and target.exists():
                    target.unlink() # Delete newly created file
            return False

    @staticmethod
    def apply_whole_file(file_path: str, content: str):
        """Safely overwrite or create a file."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
