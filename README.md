# StarStream Monorepo

**Real-time Broadcasting Ecosystem for StarHTML**

Convention over Configuration for building real-time collaborative applications with StarHTML.

## 📦 Packages

This monorepo contains the StarStream ecosystem:

| Package | Description | Install |
|---------|-------------|---------|
| **starstream** | Core broadcasting with zero config | `pip install starstream` |
| **starstream-loro** | CRDT integration for collaborative editing | `pip install starstream-loro` |
| **starstream-pocketbase** | Database persistence with auto-broadcast | `pip install starstream-pocketbase` |

## 🚀 Quick Start

The fastest way to start a new project is using the StarStream CLI (requires [uv](https://astral.sh/uv)):

```bash
uvx starstream init my-app
cd my-app
uv run app.py
```

### Manual Installation
```python
from starhtml import *
from starstream import StarStreamPlugin
...
StarStream comes with a pre-configured `SKILL.md` for AI agents. This skill provides expert instructions for building real-time applications, managing presence, and integrating Loro or PocketBase.

## 📁 Structure

```
starstream-monorepo/
├── packages/
│   ├── starstream/              # Core package
│   │   ├── starstream/          # Source code
│   │   ├── tests/               # 114 tests
│   │   └── examples/            # Usage examples
│   ├── starstream-loro/         # CRDT plugin
│   └── starstream-pocketbase/   # Database plugin
├── README.md
└── LICENSE
```

## 📚 Documentation

- [packages/starstream/README.md](packages/starstream/README.md)
- [packages/starstream-loro/README.md](packages/starstream-loro/README.md)
- [packages/starstream-pocketbase/README.md](packages/starstream-pocketbase/README.md)

## 📝 License

MIT