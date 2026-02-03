# Interactive Mode

AkitaLLM puts you in control.

## The Problem
Traditional AI coding tools generate code and apply it automatically, sometimes introducing bugs or unwanted changes.

## The Solution: Human-in-the-Loop
With AkitaLLM's interactive mode, you review every plan before execution.

### How to Use
```bash
akita solve "Refactor the login function" --interactive
```

### The Flow
1. **Akita generates a plan** (a Unified Diff).
2. **You review it** in your terminal.
3. **Choose an action**:
   - `[A]pprove`: Apply the changes.
   - `[R]efine`: Provide feedback and get a new plan.
   - `[C]ancel`: Discard everything.

### Reasoning Trace
Use `--trace` to see why the AI made specific decisions:
```bash
akita solve "Add logging" --trace
```

This will show which files were analyzed and how context was selected.
