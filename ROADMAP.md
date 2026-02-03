# AkitaLLM Roadmap: The Path to v1.0.0 🚀

This document outlines the strategic steps required to transition AkitaLLM from Beta to a stable, production-ready v1.0.0.

## 🎯 Phase 1: Robust Execution (The Core)
- [ ] **Complete DiffApplier**: Implement full Unified Diff application with rollback capabilities.
- [ ] **Atomicity**: Ensure multi-file changes are applied as a single transaction (all or nothing).
- [ ] **Pre-flight Validation**: Automatically run tests or linters on the proposed diff before application.

## 🧠 Phase 2: Intelligent Context (AST & Semantics)
- [ ] **AST Integration**: Use `Tree-sitter` to parse code structure and allow granular item targeting (classes, methods).
- [ ] **Dependency Grafting**: Automatically include relevant imported files in the LLM context.
- [ ] **Context Budgeting**: Intelligent token management to avoid hitting context limits on large files.

## 🔌 Phase 3: Plugin Architecture (Extensibility)
- [ ] **Plugin Engine**: Implement a plugin system using Python `entry_points`.
- [ ] **Core Plugins**: Move standard tools (Linter, Git) to a plugin-based internal structure.
- [ ] **Third-Party Support**: Create a SDK/Template for developers to build their own AkitaLLM plugins.

## 🔄 Phase 4: Interactive Feedback Loop
- [ ] **Plan Refinement**: Allow users to interactively edit and approve plans before generation.
- [ ] **Reasoning Logs**: Visual representation of the "thought process" for easier debugging.
- [ ] **Conversational Refactoring**: Maintain state across multiple commands for iterative problem solving.

## 📈 Phase 5: Production & Enterprise Grade
- [ ] **Binary Releases**: Compile AkitaLLM as standalone binaries (Windows, Linux, macOS).
- [ ] **Local Search (RAG)**: Integrate local vector database (FAISS/ChromaDB) for high-performance context retrieval.
- [ ] **Comprehensive Documentation Site**: Professional technical documentation outside of GitHub.

---

*“Engineering is not about the first version, it’s about the tenth version’s stability.”*
