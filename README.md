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

@rt("/chat")
@sse
async def chat(msg: str):
    yield elements(Div(msg), "#chat", "append")
    # Auto-broadcasts to all clients!
```

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