# StarStream Loro

**CRDT Integration for StarStream**

Provides conflict-free replicated data types (CRDT) support for collaborative editing in StarStream applications.

## Installation

```bash
pip install starstream-loro
```

## 🛠 AI Agent Skills

StarStream includes a `SKILL.md` for AI agents. This skill provides expert instructions for building real-time apps.
Agents can install it via:

```bash
npx skills add renatocaliari/starstream
```

## Features

- Loro CRDT synchronization
- Collaborative text editing
- Canvas with CRDTs
- Delta synchronization
- Version history

## Quick Start

```python
from starhtml import *
from starstream import StarStreamPlugin
from starstream_loro import LoroPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)
loro = LoroPlugin(stream)

@rt("/doc/{doc_id}/edit", methods=["POST"])
async def edit(doc_id: str, delta: bytes):
    await loro.receive_delta(doc_id, "user1", delta)
    # Auto-merges with other users' changes!
```

## License

MIT