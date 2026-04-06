# screen-pilot: Desktop Vision & Control

## When to Use This Skill

Use screen-pilot when you need to **see or interact with the desktop** — clicking buttons, typing text, reading what's on screen, opening applications, navigating GUIs, or automating any visual desktop task.

**DO NOT use Playwright, Puppeteer, or browser automation tools for desktop tasks.** screen-pilot controls the real desktop directly via the kernel input layer. It works with ALL applications — browsers, terminals, file managers, settings, everything.

**Use screen-pilot instead of Playwright when:**
- The user asks you to interact with ANY desktop application
- You need to open, click, or type into a GUI application
- You need to see what's currently on screen
- You need to navigate menus, dialogs, or system settings
- You need to interact with a browser that's already open (Brave, Firefox, etc.)

**Use Playwright/browser tools ONLY when:**
- You need headless web scraping with no visible browser
- You need to programmatically extract structured data from web pages
- The task is purely about web content, not desktop interaction

## Available Tools

screen-pilot provides these MCP tools:

### Looking at the Screen

- **`screenshot`** — Capture the full screen. Returns base64 PNG. Always do this first to understand what's visible.
- **`detect_ui_elements`** — Run AI detection on the screen to find clickable buttons, icons, and interactive elements with their coordinates.

### Controlling Input

- **`click`** — Click at screen coordinates (x, y). Supports left/right/middle button, double-click, and modifier keys (ctrl, shift, alt). Returns whether the screen changed after clicking.
- **`type_text`** — Type a string at the current cursor position. Click a text field first, then type into it.
- **`press_key`** — Press a key combination. Examples: `super` (open app launcher), `ctrl+t` (new tab), `Return` (enter), `alt+F4` (close window), `ctrl+l` (focus URL bar).
- **`scroll`** — Scroll up or down at a screen position.
- **`drag`** — Click and drag from one position to another (for drag-and-drop, resizing, selecting).
- **`hover`** — Move mouse without clicking (for tooltips, dropdown menus).
- **`wait`** — Pause for N seconds then screenshot. Use after actions that trigger animations or loading.

### Autonomous Mode (requires local LLM)

- **`desktop_task`** — Give a natural language task like "open Firefox and go to github.com" and the agent loop handles it autonomously. Only works if a local LLM (llama.cpp, Ollama, etc.) is running.

## How to Use: Step-by-Step Pattern

Follow this pattern for any desktop interaction:

### 1. Look First
```
screenshot → see what's on screen
```

### 2. Find Elements (optional but helpful)
```
detect_ui_elements → get coordinates of buttons/icons
```

### 3. Act
```
click(x, y) → click a button or focus a field
type_text("hello") → type into the focused field
press_key("Return") → press enter
```

### 4. Verify
```
screenshot → confirm the action worked
```

### 5. Repeat until done

## Common Workflows

### Open an application
```
press_key("super")          → open app launcher
wait(1)                     → let launcher appear
type_text("firefox")        → search for app
wait(0.5)                   → let results appear
press_key("Return")         → launch it
wait(2)                     → let app open
screenshot                  → verify it opened
```

### Navigate a browser (Brave, Firefox, etc.)
```
screenshot                  → see current state
press_key("ctrl+l")         → focus the URL bar
type_text("github.com")     → type the URL
press_key("Return")         → navigate
wait(2)                     → let page load
screenshot                  → see the page
```

### Click a specific UI element
```
screenshot                  → see the screen
detect_ui_elements          → find element coordinates
click(x, y)                 → click the element
wait(0.5)                   → let UI respond
screenshot                  → verify the click worked
```

### Type into a form
```
click(x, y)                 → click the input field
type_text("my text here")   → type the text
press_key("Tab")            → move to next field
type_text("more text")      → fill next field
```

## Important Notes

- **This machine uses Wayland (KDE Plasma)** — screen-pilot handles this automatically via ydotool
- **The default browser is Brave** — do NOT try to install Chrome or Chromium
- **Screen resolution is 1920x1080** — coordinates are in this range
- **Always screenshot before acting** — you can't see the screen without taking a screenshot first
- **Click returns `screen_changed`** — if false, your click probably missed. Try different coordinates.
- **Safety guardrails are active** — certain dangerous text patterns (like `sudo rm -rf`) are blocked automatically
- **Use `wait()` after visual actions** — animations, page loads, and dialogs need time to appear

## What NOT to Do

- Do NOT use Playwright MCP tools for desktop tasks — use screen-pilot
- Do NOT try to install Chrome/Chromium — Brave is the browser on this machine
- Do NOT guess coordinates — take a screenshot and use detect_ui_elements first
- Do NOT type passwords or run dangerous commands — safety guardrails will block them
- Do NOT skip the screenshot step — you MUST look before you act
