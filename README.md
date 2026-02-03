```text
     _      _   _ _        _     _     __  __ 
    / \    | | _(_) |_ __ _| |   | |   |  \/  |
   / _ \   | |/ / | __/ _` | |   | |   | |\/| |
  / ___ \  |   <| | || (_| | |___| |___| |  | |
 /_/   \_\ |_|\_\_|\__\__,_|_____|_____|_|  |_|
                                               
```

# AkitaLLM
### A deterministic, local-first AI orchestrator for software engineers.

---

## What is AkitaLLM?

AkitaLLM is not another "AI wrapper." It is a command-line utility designed for developers who value engineering rigor over generative "magic." It treats Large Language Models as non-deterministic execution engines that must be constrained within a strict, auditable pipeline: **Analyze → Plan → Execute → Validate**.

Built as a local-first tool, it provides you with an AI-augmented workflow that respects your project's context, follows security best practices, and prioritizes structured output over conversational noise.

---

## Why AkitaLLM exists

Most current AI tools (ChatGPT, Copilot, Cursor) operate in a "black-box" conversational mode. They are excellent at text generation but often fail at **software engineering**, which requires:
- **Project-Level Context**: Understanding how a change in `utils.py` affects `main.py`.
- **Previsibilty**: Knowing exactly what the AI intends to do before it modifies a single byte.
- **Verification**: Automatically ensuring that proposed changes don't break existing logic.

AkitaLLM was built to bridge this gap, treating AI as a component of a larger, human-controlled engineering process.

---

## The Engineering Difference

| Feature | Generic AI Tools | AkitaLLM |
| :--- | :--- | :--- |
| **Logic** | Conversational / Guesswork | Analyze → Plan → Execute → Validate |
| **Control** | Autocomplete / Chat | Explicit technical plans & reviewable Diffs |
| **Security** | Cloud-heavy | Local-first, respects `.gitignore` and `.env` |
| **Validation** | Post-facto manual review | Automated local test execution |
| **Philosophy** | "It just works" (Hype) | "Understand the internals" (Engineering) |

---

## Core Principles

1. **Local-First**: Your code remains on your machine. AkitaLLM orchestrates local models (via Ollama) or remote APIs (via LiteLLM) through encrypted, controlled channels.
2. **Contextual Awareness**: It uses recursive file scanning and structure analysis to build a high-fidelity map of your project before making suggestions.
3. **No Magic**: No hidden prompts, no mysterious "thinking" phases. All actions are logged, auditable, and based on standard engineering patterns.
4. **Tool-Driven**: AI is a user of tools (linters, test runners, AST parsers), not a replacement for them.

---

## Key Features

- **Structural Code Review**: Detailed analysis of bugs, style, performance, and security risks with prioritized severity levels.
- **Technical Planning**: Generation of step-by-step implementation plans in Markdown for complex feature requests.
- **Actionable Diffs**: Proposed changes are generated as standard Unified Diffs for human review before application.
- **Environment Isolation**: Supports `.env` and local configuration storage (`~/.akita/`) to keep secrets safe.
- **Model Agnostic**: Seamlessly switch between GPT-4o, Claude 3.5, Llama 3, and more.

---

## Installation

AkitaLLM is available on PyPI. It requires Python 3.10 or later.

```bash
pip install akitallm
```

---

## Usage

### 1. Project Initialization
Run any command to trigger the initial configuration and onboarding.
```bash
akita review .
```

### 2. Strategic Code Review
Analyze a directory for potential architectural risks and bugs.
```bash
akita review src/
```

### 3. Implementation Planning
Generate a technical plan for a specific goal.
```bash
akita plan "Implement JWT authentication with Redis-based session storage"
```

### 4. Code Problem Solving
Generate a diff to solve a precise issue or refactor a module.
```bash
akita solve "Improve error handling in the reasoning engine to prevent silent failures"
```

---

## Contributing

We are looking for engineers, not just coders. If you value robust abstractions, clean code, and predictable systems, your contribution is welcome.

Review our [CONTRIBUTING.md](CONTRIBUTING.md) to understand our engineering standards and PR workflow. High-quality PRs with test coverage are prioritized.

---

*“Understanding the internals is the first step to excellence.”*
