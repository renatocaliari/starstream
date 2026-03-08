# StarStream Monorepo

**Real-time Broadcasting Ecosystem for StarHTML**

Convention over Configuration for building real-time collaborative applications with StarHTML.

## ✨ Features

**Core (starstream):**
- 📡 Real-time broadcasting (fire-and-forget)
- 👥 Presence tracking (who's online)
- ⌨️ Typing indicators
- 🖱️ Cursor tracking
- 💾 Message history with TTL
- 🗄️ SQLite storage (automatic)

**Plugins:**
- 🔗 **starstream-loro** - CRDT for collaborative editing
- 🗄️ **starstream-pocketbase** - Auth, admin UI, file storage

## 📦 Packages

| Package | Description | Install |
|---------|-------------|---------|
| **starstream** | Core broadcasting + SQLite storage (auto) | `pip install starstream` |
| **starstream-loro** | CRDT for collaborative editing | `pip install starstream-loro` |
| **starstream-pocketbase** | Auth, admin UI, file storage | `pip install starstream-pocketbase` |

## 🚀 Quick Start

### For New Projects
Create a ready-to-run StarHTML app with StarStream pre-configured:
```bash
uvx starstream init my-app
cd my-app && uv run app.py
```

### For Existing Projects
Add StarStream to your current StarHTML app automatically (detects uv/pip):
```bash
uvx starstream add --file app.py
```
*This command installs the package and injects the `StarStreamPlugin` boilerplate into your code.*

## 🛠 AI Agent Skills

StarStream includes a `SKILL.md` for AI agents. This skill provides expert instructions for building real-time apps.
Agents can install it via:
```bash
npx skills add renatocaliari/starstream
```

## 📁 Structure

```
starstream-monorepo/
├── packages/
│   ├── starstream/              # Core package
│   ├── starstream-loro/         # CRDT plugin
│   └── starstream-pocketbase/   # Database plugin
├── skills/
│   └── starstream/              # Agent skill (SKILL.md)
├── README.md
└── LICENSE
```

## 📚 Documentation

- [packages/starstream/README.md](packages/starstream/README.md)
- [packages/starstream-loro/README.md](packages/starstream-loro/README.md)
- [packages/starstream-pocketbase/README.md](packages/starstream-pocketbase/README.md)

## 📝 License

MIT
