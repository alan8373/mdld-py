# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`dwim2` is an early-stage Python project. Based on installed dependencies, it is being built around:

- **`graphifyy`** — turns folders of code, docs, papers, images, or videos into a queryable knowledge graph (GraphRAG)
- **`tree-sitter`** + language grammars — AST-based parsing of source code across 20+ languages (Python, JS/TS, Go, Rust, C/C++, Java, Ruby, etc.)
- **`networkx`** — graph computation and traversal

## Environment

- Python 3.14, managed via `.venv`
- Activate: `source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt` (once created)
- Run a script: `.venv/bin/python <script.py>`
