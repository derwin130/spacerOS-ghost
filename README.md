# GHOST

GHOST is the operational command bot powering SpacerOS — an immersive operations terminal designed for Star Citizen organizations.

---

# Current Features

## Phase 1

- Operation creation
- Active operation tracking
- Crew assignment
- Readiness tracking
- Dispatch updates
- Persistent cloud hosting
- SQLite-backed persistence
- Slash command support

---

## Phase 1.5

- Multi-server (guild) isolation
- Dispatch channel routing
- Operation leave command
- Improved embeds and error handling
- Risk-based embed coloring
- Alpha testing support for external organizations

---

# Commands

## Operations

### Create Operation
```bash
/op-create
```

### List Active Operations
```bash
/op-list
```

### View Operation Status
```bash
/op-status
```

### Join Operation
```bash
/op-join
```

### Leave Operation
```bash
/op-leave
```

### Mark Ready
```bash
/op-ready
```

### Close Operation
```bash
/op-close
```

---

## Dispatch System

### Configure Dispatch Feed
```bash
/setup-dispatch
```

### Post Dispatch Update
```bash
/dispatch
```

---

# Infrastructure

- Python
- discord.py
- SQLite
- Google Cloud VM
- systemd
- GitHub

---

# Architecture

```text
Discord Server
    ↓
GHOST Bot
    ↓
SpacerOS Operations Terminal
    ↓
SQLite Database
```

---

# Project Status

Current Development Phase:
```text
Phase 1.5 — Alpha Testing
```

Current Focus:
- operational testing
- UX refinement
- embed polish
- multi-server stability
- dispatch flow improvements

---

# Planned Features

## Phase 1.6

- Discord scheduled event creation
- Structured operation scheduling
- Timezone support
- Event-linked operations

## Future Roadmap

- Interactive web dashboard
- Fleet registry system
- Personnel certifications
- AI tactical relay
- Organization analytics
- Economy systems

---

SpacerOS is currently in active development.
