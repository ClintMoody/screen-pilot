---
name: screen-pilot
description: Desktop vision and control via screen-pilot MCP server. Take real screenshots, click, type, scroll, drag, detect UI elements with AI vision, and run autonomous desktop tasks. Works with any application on the desktop without needing a browser engine.
version: 1.0.0
author: clintm
license: MIT
metadata:
  hermes:
    tags: [MCP, Desktop, Automation, Vision, Screen Control]
    related_skills: [native-mcp]
---

# screen-pilot: Desktop Vision & Control

screen-pilot controls the **real desktop** — the actual screen, mouse, and keyboard at the OS level. It works with every application: browsers (Brave, Firefox, etc.), terminals, file managers, settings panels, native apps, dialogs, and anything else visible on screen.

## When to Use screen-pilot

Use screen-pilot when you need to:
- **See the screen** — take a real screenshot of whatever is currently visible
- **Interact with any desktop application** — click buttons, type text, press keys, scroll
- **Navigate a browser that's already installed** — Brave, Firefox, or whatever the user has
- **Open applications** — press Super to open the launcher, type the app name, press Enter
- **Automate GUI tasks** — fill forms, navigate menus, adjust settings, drag files

### screen-pilot vs browser tools

| Capability | screen-pilot | Browser tools (Playwright, etc.) |
|---|---|---|
| Works with any desktop app | Yes | No (browser only) |
| Needs Chromium installed | No | Yes |
| Works with user's existing browser | Yes (Brave, Firefox, etc.) | No (uses own Chromium) |
| Sees real screen state | Yes | No (headless render) |
| Controls mouse/keyboard | Yes (OS-level) | No (DOM-level) |

**Use screen-pilot** for desktop GUI interaction. **Use browser tools** only for headless web scraping where you don't need a visible browser.

## Tools

| Tool | What it does |
|------|-------------|
| `mcp_screen-pilot_screenshot` | Capture the real desktop screen as PNG |
| `mcp_screen-pilot_click` | Click at screen coordinates (any app) |
| `mcp_screen-pilot_type_text` | Type text into the focused field/app |
| `mcp_screen-pilot_press_key` | Press key combos: `super`, `ctrl+t`, `ctrl+l`, `Return` |
| `mcp_screen-pilot_scroll` | Scroll up/down at a position |
| `mcp_screen-pilot_drag` | Drag from one point to another |
| `mcp_screen-pilot_hover` | Move mouse without clicking |
| `mcp_screen-pilot_wait` | Pause then screenshot (for load times) |
| `mcp_screen-pilot_detect_ui_elements` | AI vision to find clickable elements |
| `mcp_screen-pilot_desktop_task` | Autonomous task loop (needs local LLM) |

## Usage Pattern

### 1. Look first (always)
```
mcp_screen-pilot_screenshot
```

### 2. Act
```
mcp_screen-pilot_click(x=500, y=300)
mcp_screen-pilot_type_text(text="search query")
mcp_screen-pilot_press_key(key="Return")
```

### 3. Verify
```
mcp_screen-pilot_screenshot
```

## Common Workflows

**Open an app:**
`press_key("super")` → `wait(1)` → `type_text("app name")` → `press_key("Return")` → `wait(2)` → `screenshot`

**Navigate in a browser:**
`press_key("ctrl+l")` → `type_text("url")` → `press_key("Return")` → `wait(2)` → `screenshot`

**Click a UI element:**
`screenshot` → `detect_ui_elements` → `click(x, y)` → `screenshot`

## Tips

- Always screenshot before acting — you can't see the screen otherwise
- If `click` returns `screen_changed: false`, your click missed — try different coordinates
- Use `wait` after actions that trigger loading or animations
- Use `detect_ui_elements` when you're not sure where things are on screen
- Screen resolution is typically 1920x1080
