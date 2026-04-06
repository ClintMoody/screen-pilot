# screen-pilot: Instructions for AI Agents

> Add this file to your agent's context when using screen-pilot.

## What screen-pilot Does

screen-pilot gives you direct control of the real Linux desktop — the actual screen, mouse, and keyboard. It works with **every application** on the desktop without needing a browser engine, Chromium, or any special software.

## When to Use screen-pilot

Use screen-pilot tools for any task involving the desktop GUI:
- Interacting with the user's existing browser (whatever they have installed)
- Opening and controlling native desktop applications
- Navigating system settings, file managers, terminals
- Filling forms, clicking buttons, typing text in any visible application
- Taking screenshots to see what's currently on screen

## When NOT to Use screen-pilot

- Headless web scraping where no visible browser is needed (use Playwright/Puppeteer)
- Programmatic DOM manipulation or JavaScript execution (use browser devtools)

## Tool Reference

| Tool | Purpose | Example |
|------|---------|---------|
| `screenshot` | See the screen (always do this first) | `screenshot()` |
| `click` | Click at coordinates | `click(x=500, y=300)` |
| `type_text` | Type into focused field | `type_text(text="hello")` |
| `press_key` | Press key combo | `press_key(key="ctrl+t")` |
| `scroll` | Scroll at position | `scroll(x=500, y=300, direction="down")` |
| `drag` | Drag between points | `drag(from_x=100, from_y=100, to_x=500, to_y=500)` |
| `hover` | Move mouse (no click) | `hover(x=500, y=300)` |
| `wait` | Pause then screenshot | `wait(seconds=2)` |
| `detect_ui_elements` | Find clickable elements | `detect_ui_elements()` |
| `desktop_task` | Autonomous task (needs local LLM) | `desktop_task(task="open Firefox")` |

## The Pattern

1. **Screenshot** — see what's on screen
2. **Act** — click, type, press keys
3. **Screenshot** — verify it worked
4. **Repeat** until task is done

## Useful Key Combinations

| Keys | Action |
|------|--------|
| `super` | Open application launcher |
| `ctrl+l` | Focus browser URL bar |
| `ctrl+t` | New browser tab |
| `ctrl+w` | Close current tab |
| `Return` | Enter / confirm |
| `Tab` | Next field |
| `alt+F4` | Close window |
| `ctrl+c` / `ctrl+v` | Copy / paste |

## Important Notes

- You MUST take a screenshot before acting — you cannot see the screen otherwise
- The `click` tool returns `screen_changed: true/false` — if false, your click missed
- Use `wait` after actions that trigger page loads or animations
- Safety guardrails block dangerous text patterns automatically
- These tools work at the OS level — they control the real mouse and keyboard
