# Plugin System

AkitaLLM is designed to be infinitely extensible. You can add new capabilities (tools) to the reasoning engine by creating official or third-party plugins.

## Technical Architecture

AkitaLLM uses a **hybrid plugin model**:
1.  **Internal Plugins**: Located in `akita/plugins/`.
2.  **External Plugins**: Scalable third-party packages installed via `pip` that register themselves using Python `entry_points`.

---

## Creating Your First Plugin

### 1. The Plugin Interface
Every plugin must inherit from `AkitaPlugin` and implement the required properties and methods.

```python
from akita.core.plugins import AkitaPlugin
from typing import List, Dict, Any

class MyAwesomePlugin(AkitaPlugin):
    @property
    def name(self) -> str:
        return "awesome_tool"

    @property
    def description(self) -> str:
        return "Provides advanced cosmic calculations."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "calculate_gravity",
                "description": "Calculates gravity based on planet mass.",
                "parameters": {"mass": "float", "radius": "float"},
                "func": my_internal_function
            }
        ]

def my_internal_function(mass: float, radius: float) -> str:
    return f"Gravity: { (6.674e-11 * mass) / (radius**2) } m/s2"
```

### 2. Registration
To make your plugin discoverable by AkitaLLM, register it in your `pyproject.toml`:

```toml
[project.entry-points."akitallm.plugins"]
awesome = "my_package.module:MyAwesomePlugin"
```

### 3. How Discovery Works
When `ReasoningEngine` starts, the `PluginManager` scans:
1.  The local `akita/plugins/` directory.
2.  All installed Python packages for the `akitallm.plugins` entry point group.

---

## Best Practices
- **Atomic Tools**: Keep tools focused on a single responsibility.
- **Documentation**: Provide clear, technical descriptions for each tool so the LLM knows exactly when and how to use it.
- **Error Handling**: Tools should return clear error messages that the LLM can understand and react to.
