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

```python
from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)  # That's it!

# When history or persistence is enabled, StarStream uses SQLite as the default backend.
# No configuration required for local persistence.
```

## 🛠 Skills & Agent Support

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