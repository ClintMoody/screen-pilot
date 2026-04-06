# screen-pilot

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux-orange.svg)](https://kernel.org)

**Give AI agents eyes and hands on your Linux desktop.**

Screenshot capture, UI element detection, and mouse/keyboard control -- exposed as an MCP server that any AI agent can use, plus a CLI for humans.

[Quick Start](#quick-start) | [Agent Setup](#agent-setup) | [CLI Reference](#cli-reference) | [MCP Tools](#mcp-tools-reference) | [Safety](#safety) | [Configuration](#configuration)

---

## Security Warning

> **screen-pilot grants AI agents kernel-level control of your keyboard and mouse.** This is not a sandboxed or simulated environment. Actions are real and affect your live desktop.

**What this means:**
- Any process with uinput access can type arbitrary commands into any terminal, including `sudo` prompts, across all sessions
- A prompt injection attack (malicious text on a webpage the agent reads) could cause the agent to execute attacker-controlled keystrokes
- There is no display-server boundary -- uinput operates at the kernel input layer, below Wayland's isolation model

**Built-in mitigations:** Config-driven safety guardrails, dry-run mode, emergency stop hotkey, action logging

**You should:** Start with `dry_run = true`, never grant the agent passwordless sudo, review the safety config before enabling autonomous mode. See [Safety](#safety) for full details.

---

## Quick Start

**Install:**

```bash
curl -sSL https://raw.githubusercontent.com/clintm/screen-pilot/main/install.sh | bash
```

Or clone and run the interactive installer:

```bash
git clone https://github.com/clintm/screen-pilot.git
cd screen-pilot && ./install.sh
```

**Start the server:**

```bash
screen-pilot up
```

**Connect your agent:**

```bash
claude mcp add screen-pilot --transport sse http://localhost:7222/mcp/sse
```

That's it. Your agent can now see and control your desktop.

---

## How It Works

```
+--------------------------------------------------+
|  Claude Code / Codex / OpenCode / Any Agent      |
|  +-> MCP protocol -> screen-pilot MCP server     |
+--------------------------------------------------+
|  Human terminal                                  |
|  +-> screen-pilot CLI -> HTTP -> same server     |
+--------------------------------------------------+
|  systemd user services (always-on)               |
|  +-- screen-pilot.service (MCP + HTTP)           |
|  +-- ydotool.service (input control)             |
+--------------------------------------------------+
|  Optional: local LLM (llama.cpp/Ollama/etc.)     |
|  +-- auto-detected for autonomous desktop_task   |
+--------------------------------------------------+
```

**No local LLM required.** Your calling agent (Claude, Codex, etc.) IS the brain. screen-pilot provides the eyes and hands through low-level primitives: `screenshot`, `click`, `type_text`, `press_key`, `scroll`, `drag`, `hover`, `wait`, and `detect_ui_elements`.

**Optional autonomous mode:** If a local LLM is running (llama.cpp, Ollama, LM Studio, or vLLM), the `desktop_task` tool runs a full screenshot->detect->reason->act loop without tying up your calling agent.

---

## Install

### Supported Platforms

| Platform | Package Manager | Session Types |
|----------|----------------|--------------|
| Arch / CachyOS | pacman | Wayland, X11 |
| Ubuntu / Debian | apt | Wayland, X11 |

### What Gets Installed

| Component | Purpose | Required |
|-----------|---------|----------|
| ydotool | Mouse/keyboard control (Wayland + X11) | Yes |
| spectacle/grim/maim | Screenshot capture (auto-detected) | Yes |
| python-evdev | Kernel-level input fallback | Yes |
| OmniParser V2 | UI element detection (YOLO) | Optional (`--no-omniparser`) |
| Miniconda | Python environment isolation | If not present |

### Install Options

```bash
# Full install (interactive TUI)
./install.sh

# Lightweight (no OmniParser, no GPU dependencies)
./install.sh --no-omniparser

# Non-interactive
./install.sh --yes

# Specific version
./install.sh --version v1.0.0

# Uninstall
./install.sh --uninstall
```

### Post-Install Health Check

```bash
screen-pilot status
```

```
screen-pilot running (port 7222)
  Screenshot:  spectacle (Wayland)
  OmniParser:  idle (unloaded)
  LLM:         nemotron-cascade @ localhost:8081 (text-only, reasoning)
  Safety:      3 blocked patterns, 0 blocked regions
```

---

## Agent Setup

### Claude Code

```bash
claude mcp add screen-pilot --transport sse http://localhost:7222/mcp/sse
```

### Codex

```bash
codex mcp add screen-pilot --transport sse http://localhost:7222/mcp/sse
```

### OpenCode

Add to `~/.config/opencode/config.json`:

```json
{
  "mcpServers": {
    "screen-pilot": {
      "url": "http://localhost:7222/mcp/sse"
    }
  }
}
```

### Generic (REST API)

```bash
# Take a screenshot
curl -X POST http://localhost:7222/api/screenshot | jq .

# Click at position
curl -X POST http://localhost:7222/api/click \
  -H "Content-Type: application/json" \
  -d '{"x": 500, "y": 300}'

# Detect UI elements
curl -X POST http://localhost:7222/api/detect_ui_elements | jq .
```

---

## CLI Reference

### Service Management

```bash
screen-pilot up              # Start the service
screen-pilot down            # Stop the service
screen-pilot status          # Health, detected LLM, loaded models
screen-pilot logs [--follow] # Tail server logs
```

### Desktop Control

```bash
screen-pilot screenshot [--output PATH] [--json]
screen-pilot click X Y [--right] [--double] [--mod ctrl,shift]
screen-pilot type "text here"
screen-pilot key "ctrl+t"
screen-pilot scroll X Y [--up] [--amount N]
screen-pilot drag X1 Y1 X2 Y2
screen-pilot hover X Y
screen-pilot wait [SECONDS]
screen-pilot detect [--json]
```

### Autonomous Task

```bash
screen-pilot task "open Firefox and search for screen-pilot"
screen-pilot task "enable dark mode" --max-steps 10
screen-pilot task "open settings" --dry-run
```

### Configuration

```bash
screen-pilot config          # TUI config manager
screen-pilot install         # TUI installer (re-run)
screen-pilot uninstall       # TUI uninstaller
screen-pilot detect-backend  # Re-probe for local LLM
```

---

## MCP Tools Reference

### Low-Level Primitives (always available, no LLM needed)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `screenshot` | `format?: "base64"\|"path"` | Base64 PNG or file path |
| `click` | `x, y, button?, clicks?, modifiers?` | `{success, screen_changed}` |
| `type_text` | `text, modifiers?` | `{success}` |
| `press_key` | `key` (e.g. "ctrl+t", "super") | `{success}` |
| `scroll` | `x, y, direction, amount?` | `{success}` |
| `drag` | `from_x, from_y, to_x, to_y` | `{success}` |
| `hover` | `x, y` | `{success}` |
| `wait` | `seconds?` (default 1.0) | `{screenshot}` |
| `detect_ui_elements` | `screenshot_path?` | `{elements: [...]}` |

### High-Level (requires local LLM)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `desktop_task` | `task, max_steps?, dry_run?` | `{status, steps_taken, log}` |

**Key behaviors:**
- `click` auto-captures before/after screenshots and reports `screen_changed: true/false`
- `detect_ui_elements` lazy-loads OmniParser on first call, auto-unloads after 60s idle to free VRAM
- `desktop_task` returns a helpful error if no local LLM is found, suggesting you use the primitives instead

---

## LLM Backend (Optional)

screen-pilot auto-detects running local LLM servers on startup:

| Backend | Default Port | Detection |
|---------|-------------|-----------|
| llama.cpp | 8080-8090 | `/v1/models` with `owned_by: llamacpp` |
| Ollama | 11434 | `/api/tags` |
| LM Studio | 1234 | `/v1/models` |
| vLLM | 8000 | `/v1/models` |

**Check what's detected:**

```bash
screen-pilot detect-backend
```

**Manual override** in `~/.config/screen-pilot/config.toml`:

```toml
[backend]
url = "http://localhost:8081/v1/chat/completions"
model = "nemotron-cascade"
```

**Vision vs text-only:** If the model supports image input, `desktop_task` sends screenshots directly. If text-only (like Nemotron-Cascade), it sends OmniParser text descriptions instead. Both work.

---

## Safety

### Default Guardrails

```toml
[safety]
max_steps_per_task = 30          # Force-stop after this many actions
min_action_delay = 0.5           # Cooldown between actions (seconds)
emergency_stop = "ctrl+shift+escape"  # Kill switch
dry_run = false                  # Log actions without executing

[safety.blocked_patterns]
patterns = ["sudo rm -rf", ":(){ :|:&", "dd if="]

[safety.blocked_regions]
# regions = [{x = 1700, y = 0, w = 220, h = 50, label = "system tray"}]
regions = []
```

### How It Works

1. **Before every action**, the safety engine checks against all rules
2. **Blocked patterns** prevent the agent from typing dangerous commands
3. **Blocked regions** prevent clicks in sensitive screen areas
4. **Step limits** force-stop runaway task loops
5. **Emergency stop** (Ctrl+Shift+Escape) immediately halts any running task

### Dry-Run Mode

Test the agent's decision-making without executing any actions:

```bash
screen-pilot task "open Firefox" --dry-run
```

Or set globally in config:

```toml
[safety]
dry_run = true
```

### Honest Limitations

- Guardrails are application-level, not security boundaries. A compromised server process bypasses them.
- `allowed_apps` window title matching is best-effort on Wayland.
- uinput access is kernel-level. There is no way to restrict it to specific applications.
- **Start with dry-run mode** until you trust the agent's decisions.

---

## Configuration

Config file: `~/.config/screen-pilot/config.toml`

Or use the TUI: `screen-pilot config`

### Full Reference

```toml
[server]
host = "127.0.0.1"       # Bind address
port = 7222               # HTTP + MCP port

[capture]
tool = "auto"             # "auto", "spectacle", "grim", "maim"

[input]
socket = "/run/user/1000/.ydotool_socket"

[omniparser]
weights_dir = "~/.local/share/screen-pilot/weights"
auto_download = true      # Download weights on first detect call
idle_unload_seconds = 60  # Free VRAM after idle
device = "auto"           # "auto", "cuda", "cpu"

[backend]
# Auto-detected. Uncomment to override:
# url = "http://localhost:8081/v1/chat/completions"
# model = "nemotron-cascade"

[safety]
max_steps_per_task = 30
min_action_delay = 0.5
confirm_actions = []
emergency_stop = "ctrl+shift+escape"
dry_run = false

[safety.blocked_patterns]
patterns = ["sudo rm -rf", ":(){ :|:&", "dd if="]

[safety.blocked_regions]
regions = []

[safety.allowed_apps]
window_titles = []
```

---

## Architecture

```
src/screen_pilot/
+-- server.py      # FastMCP + FastAPI server (10 MCP tools + HTTP API)
+-- capture.py     # Screenshot (auto-detects spectacle/grim/maim)
+-- input.py       # ydotool wrapper (click, type, key, scroll, drag, hover)
+-- detect.py      # OmniParser YOLO detection (lazy load, idle VRAM unload)
+-- backend.py     # LLM auto-detection (llama.cpp, Ollama, LM Studio, vLLM)
+-- loop.py        # Autonomous task loop (screenshot->detect->reason->act)
+-- safety.py      # Guardrails (blocked patterns, regions, step limits)
+-- diff.py        # Screenshot diffing (action verification)
+-- config.py      # TOML config loading with defaults
+-- cli.py         # Typer CLI (thin HTTP client)
+-- tui/           # Textual TUI (installer, config, uninstaller)
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `screen-pilot: command not found` | Not installed or not in PATH | Re-run installer |
| `server is not running` | Service not started | `screen-pilot up` |
| ydotool has no effect | ydotoold not running | `systemctl --user start ydotool` |
| `PermissionError: /dev/uinput` | Not in input group | `sudo usermod -aG input $USER`, re-login |
| Screenshot blank | Wrong display env vars | Check WAYLAND_DISPLAY and DISPLAY |
| OmniParser CUDA error | Wrong torch/CUDA version | Reinstall torch with correct CUDA wheel |
| LLM not detected | Non-standard port | Set `url` in `[backend]` config section |
| `desktop_task` error | No local LLM running | Use low-level tools or start llama.cpp/Ollama |

---

## Contributing

### Adding a Screenshot Backend

Add the tool command to `TOOL_COMMANDS` in `capture.py` and include it in `DETECTION_ORDER`.

### Adding an LLM Backend

Add a probe target to `PROBE_TARGETS` in `backend.py` with the backend name, URL pattern, and port range.

### Adding a Detector

Implement the same interface as `OmniParserDetector` in `detect.py`: `load()`, `unload()`, `detect(screenshot_path)`.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Your agent can now see and control your desktop.**

`screen-pilot up` and go.

</div>
