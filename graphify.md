# Graphify — usage guide for AI agents

> Reference for any future iteration of the assistant to build and query a
> **Graphify knowledge graph** of this project.
> **Everything below was verified against the installed CLI (`graphifyy 0.9.5`)
> and the package source on 2026-07-03**, not just the online docs.

## What Graphify is
Turns a folder of code, SQL schemas, scripts, docs, PDFs, and images into a
**queryable knowledge graph**. Code is parsed locally with Tree-sitter; docs/
PDFs/images are extracted by an LLM. Symbols + relationships are clustered
(NetworkX + Leiden) into a persistent `graph.json` you can query later or serve
to an assistant over **MCP**. Repo: [safishamsi/graphify](https://github.com/safishamsi/graphify).

## Install status on THIS machine ✅
- **Installed** via `uv tool install "graphifyy[mcp]"` → `graphifyy==0.9.5`.
- Two executables on PATH (`C:\Users\IT\.local\bin`, on persistent user PATH):
  - **`graphify`** — the CLI (build/query/manage)
  - **`graphify-mcp`** — the MCP server (`python -m graphify.serve`)
- Confirm anytime: `graphify --version` (→ `graphify 0.9.5`).
- To reinstall/upgrade: `uv tool install --upgrade "graphifyy[mcp]"`.

## API key — needed to BUILD, not to QUERY
Code parsing is local. Building a graph over **docs/PDFs/images** calls an LLM.
`extract` auto-detects a backend from whichever key is set:
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # claude backend (default if set)
# or GEMINI_API_KEY/GOOGLE_API_KEY, OPENAI_API_KEY, MOONSHOT_API_KEY (kimi), DEEPSEEK...
```
Backends: `gemini | kimi | claude | openai | deepseek | ollama`. The `claude`
backend can also drive the local Claude CLI (subscription) instead of a raw key.
Self-hosted: `openai` honors `OPENAI_BASE_URL`/`OPENAI_MODEL`; `claude` honors
`ANTHROPIC_BASE_URL`/`ANTHROPIC_MODEL`.
**Once `graph.json` exists, querying and serving need no key.**

---

## Build the graph
There is **no bare `graphify .`** in the CLI (that form is only the in-IDE
`/graphify` skill trigger). Use these:

```powershell
graphify extract .              # headless full build (AST + semantic LLM) → ./graphify-out/
graphify extract . --mode deep  # more aggressive INFERRED-edge extraction
graphify extract . --backend claude --model <m>   # pick backend/model explicitly
graphify update .               # re-extract CODE only, no LLM, merge into graph (fast, offline)
graphify update . --force       # allow rebuild even if it yields fewer nodes (after deletions)
graphify watch .                # rebuild automatically on code changes
graphify add <url>              # fetch a URL into ./raw and update the graph
```
Useful extract flags: `--out DIR`, `--no-cluster`, `--max-workers N`,
`--max-concurrency N` (set `1` for local LLMs), `--token-budget N`,
`--postgres <DSN>` (map a live Postgres schema), `--cargo`, `--global`.

### Output → `graphify-out/`
| File | What it is |
|------|-----------|
| `graph.json` | The graph — what you query/serve (default path everywhere) |
| `graph.html` | Interactive visualization |
| `GRAPH_REPORT.md` | Findings + suggested questions |
| `cache/` | SHA256 change-detection cache for `update` |
Add `graphify-out/` to `.gitignore` unless you intend to share the graph.

---

## Query from the CLI (no key needed)
```powershell
graphify query "how does I_mpact.py load config?"   # BFS traversal for a question
graphify query "..." --dfs --depth 3 --budget 2000  # DFS / tune depth & token cap
graphify query "..." --context call --context field # restrict to edge-context types
graphify affected "SomeSymbol"                       # IMPACT: reverse traversal — what depends on X
graphify affected "X" --relation call --depth 2
graphify path "NodeA" "NodeB"                        # shortest path between two nodes
graphify explain "SomeConcept"                       # plain-language explanation + neighbors
```
All accept `--graph <path>` (default `graphify-out/graph.json`).
Other commands: `tree` (collapsible-tree HTML), `benchmark`, `export
callflow-html`, `cluster-only`, `label` (name communities), `diagnose
multigraph`, `global add|remove|list`, `reflect`, `save-result`.

---

## MCP server — structured access for the assistant
`graphify-mcp` serves an existing `graph.json`. **Build the graph first.**
```powershell
graphify-mcp                                  # stdio, serves ./graphify-out/graph.json
graphify-mcp path/to/graph.json               # explicit graph
graphify-mcp --transport http --host 127.0.0.1 --port 8080 --api-key "$env:GRAPHIFY_API_KEY"
```
Flags: `--graph PATH`, `--transport {stdio,http}`, `--host`, `--port`,
`--api-key` (env `GRAPHIFY_API_KEY`), `--path` (HTTP mount, default `/mcp`),
`--json-response`, `--stateless`, `--session-timeout`.

### Register with Claude Code
```powershell
claude mcp add graphify -- graphify-mcp        # stdio server for this project
claude mcp list                                 # verify it's connected
```
(Currently `claude mcp list` reports none — run the add above once a graph exists.)
To also install the Graphify **skill + PreToolUse hook + CLAUDE.md section** so
`/graphify` works in-IDE: `graphify install --platform claude` (or `graphify
claude install`). This edits CLAUDE.md — only run when you want that.

### MCP tools exposed (VERIFIED from source `serve.py`)
| Tool | Params (required in **bold**) | Purpose |
|------|-------------------------------|---------|
| `query_graph` | **question**, mode=bfs\|dfs, depth=3, token_budget=2000, context_filter[] | Search graph, returns node/edge context |
| `get_node` | **label** | Full details for one node (label or ID) |
| `get_neighbors` | **label**, relation_filter | Direct neighbors + edge details |
| `get_community` | **community_id** (int, 0-indexed by size) | All nodes in a community |
| `god_nodes` | top_n=10 | Most-connected nodes (core abstractions) |
| `graph_stats` | — | Node/edge/community counts + confidence breakdown |
| `shortest_path` | **source**, **target**, max_hops=8 | Shortest path between two concepts |
| `list_prs` | base, repo | Open GitHub PRs w/ CI + graph blast radius |
| `get_pr_impact` | **pr_number**, repo | Files/communities/nodes a PR touches |
| `triage_prs` | base, repo | Actionable PRs ranked by graph impact |

### MCP resources exposed
`graphify://report` (full GRAPH_REPORT.md) · `graphify://stats` ·
`graphify://god-nodes` · `graphify://surprises` · `graphify://audit`
(EXTRACTED/INFERRED/AMBIGUOUS breakdown) · `graphify://questions`.

---

## Git integration (optional)
```powershell
graphify hook install     # post-commit/post-checkout hook that rebuilds the graph
graphify hook status
```
Note: this project is **not** a git repo yet, so hooks are a no-op until `git init`.

## Recommended flow for a fresh session
1. `graphify --version` — confirm installed (if missing: `uv tool install "graphifyy[mcp]"`).
2. No `graphify-out/graph.json`? → `graphify extract .` (set `ANTHROPIC_API_KEY`
   first if the tree has docs/PDFs/images; pure-code trees can use `graphify
   update .` with no key).
3. Query directly (`graphify query "..."` / `affected` / `path` / `explain`), or
   `claude mcp add graphify -- graphify-mcp` and use `query_graph` etc.
4. After code changes: `graphify update .` (fast, offline).

## Edge confidence
Every edge is tagged `EXTRACTED` (direct), `INFERRED` (LLM-derived), or
`AMBIGUOUS`. Trust `EXTRACTED` for hard dependencies; treat `INFERRED` as hints.

## Supported inputs
Code (Tree-sitter, ~30 langs incl. `.py .ts .js .go .rs .java .c .cpp .cs .php
.rb .kt .scala .swift`) · Docs `.md .txt .rst` · Papers `.pdf` · Images `.png
.jpg .webp .gif` · live Postgres (`extract --postgres <DSN>`).

---
### Sources
- Installed CLI `graphify --help` / `graphify-mcp --help` (v0.9.5) — primary
- Package source `graphify/serve.py` (MCP tool schemas) — primary
- https://github.com/safishamsi/graphify · https://pypi.org/project/graphifyy/
