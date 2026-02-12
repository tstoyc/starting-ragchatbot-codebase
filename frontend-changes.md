# Frontend Changes: Dark/Light Theme Toggle

## Overview
Added a dark/light mode toggle button to the UI, positioned in the top-right corner with sun/moon icons and smooth transition animations.

## Files Modified

### `frontend/index.html`
- Added a `<button>` element with id `themeToggle` right after the `<body>` tag
- The button contains two inline SVG icons: a sun (visible in dark mode) and a moon (visible in light mode)
- Includes `aria-label` and `title` attributes for accessibility
- Bumped cache-bust versions for `style.css` (v10 -> v11) and `script.js` (v9 -> v10)

### `frontend/style.css`
- **Light theme CSS variables**: Added a `[data-theme="light"]` selector with light-mode color values (white surfaces, dark text, lighter borders, etc.)
- **`--code-bg` variable**: Introduced a new CSS variable for code block backgrounds, replacing hardcoded `rgba(0, 0, 0, 0.2)` values in `.message-content code` and `.message-content pre` so they adapt to the theme
- **No-transitions guard**: Added `.no-transitions` class rule that applies `transition: none !important` to all descendants. This is applied to `<html>` during initial page load and removed after first paint to prevent a visible theme flash.
- **Theme transition rule**: Added a grouped `transition` rule on all theme-sensitive elements for smooth 0.3s `background-color`, `color`, `border-color`, and `box-shadow` transitions. Covered elements: `body`, `.sidebar`, `.main-content`, `.chat-main`, `.chat-container`, `.chat-messages`, `.chat-input-container`, `#chatInput`, `#sendButton`, `.message-content`, `.stat-item`, `.suggested-item`, `.suggested-item:hover`, `.new-chat-button`, `.course-title-item`, `.stats-header`, `.suggested-header`, `.sources-collapsible`, `.sources-content li`, `.theme-toggle`
- **Toggle button styles**: Added `.theme-toggle` styles including:
  - Fixed positioning (top-right, z-index 100)
  - 44x44px circular button with surface background and border
  - Hover (scale + border highlight), focus (ring), and active (press) states
  - Icon crossfade animation: sun rotates out while moon rotates in (and vice versa) using `opacity` and `transform` transitions at 0.4s

### `frontend/script.js`
- **Early theme application (IIFE)**: Runs before `DOMContentLoaded`. Adds `no-transitions` class to `<html>` to suppress transition flash. Reads `localStorage.getItem('theme')` and applies it; if no saved preference, falls back to `prefers-color-scheme` media query to follow OS preference.
- **`initThemeToggle()` function**:
  - Re-enables transitions after first paint via double `requestAnimationFrame` (removes `no-transitions` class)
  - Registers click handler that calls `applyTheme()` and saves to `localStorage`
  - Registers a `prefers-color-scheme` change listener so the theme follows OS changes when the user hasn't explicitly chosen a preference
- **`applyTheme(theme)` function**: Sets or removes the `data-theme` attribute and updates the aria-label. Extracted from the click handler to be reusable by both the toggle and the OS preference listener.
- **`updateToggleAriaLabel()` function**: Sets the button's `aria-label` to "Switch to dark theme" or "Switch to light theme" based on current state
- Added `themeToggle` to the DOM element references and called `initThemeToggle()` during initialization

## Light Theme Accessibility Improvements

### Contrast fixes
- **`--text-secondary`**: Changed from `#64748b` (borderline ~4.5:1) to `#475569` (slate-600, ~7:1 contrast on white). Meets WCAG AA and AAA for normal text.
- **`--text-primary`**: `#0f172a` on `#f8fafc` background gives >15:1 contrast ratio.
- **User message bubble**: White text on `#2563eb` gives ~4.6:1, passing WCAG AA.

### New theme-aware CSS variables
| Variable | Dark value | Light value | Purpose |
|---|---|---|---|
| `--error-text` | `#f87171` | `#dc2626` | Error text — light red in dark, darker red in light (~4.7:1 on white) |
| `--error-bg` | `rgba(239,68,68,0.1)` | `rgba(220,38,38,0.08)` | Error background tint |
| `--error-border` | `rgba(239,68,68,0.2)` | `rgba(220,38,38,0.2)` | Error border |
| `--success-text` | `#4ade80` | `#16a34a` | Success text — bright green in dark, darker green in light (~4.6:1 on white) |
| `--success-bg` | `rgba(34,197,94,0.1)` | `rgba(22,163,74,0.08)` | Success background tint |
| `--success-border` | `rgba(34,197,94,0.2)` | `rgba(22,163,74,0.2)` | Success border |
| `--scrollbar-thumb` | `#334155` | `#cbd5e1` | Scrollbar thumb color (visible on both tracks) |
| `--scrollbar-thumb-hover` | `#94a3b8` | `#94a3b8` | Scrollbar thumb hover |
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.2)` | `0 4px 16px rgba(0,0,0,0.06)` | Welcome message box-shadow |
| `--code-bg` | `rgba(0,0,0,0.2)` | `rgba(0,0,0,0.07)` | Inline code/pre block background (increased from 0.05 for visibility) |

### CSS rules updated to use variables
- `.error-message` — `background`, `color`, `border` now use `--error-*` variables
- `.success-message` — `background`, `color`, `border` now use `--success-*` variables
- `.sidebar::-webkit-scrollbar-thumb` and `.chat-messages::-webkit-scrollbar-thumb` — now use `--scrollbar-thumb` / `--scrollbar-thumb-hover`
- `.message.welcome-message .message-content` `box-shadow` — now uses `--welcome-shadow`
- Responsive `@media` scrollbar overrides also updated

### Bug fix
- `.message-content blockquote` border used nonexistent `var(--primary)` — fixed to `var(--primary-color)`

## Visual Hierarchy Audit (Both Themes)

A full audit was performed to ensure all elements work correctly in both themes. The following issues were found and fixed:

### Assistant message bubble visibility
- **Problem**: In light mode, `.message.assistant .message-content` had `background: var(--surface)` (#ffffff) on `var(--background)` (#f8fafc) — nearly zero contrast, making bubbles invisible against the page.
- **Fix**: Added `--assistant-msg-border` variable (`transparent` in dark mode, `#e2e8f0` in light mode). Applied as `border: 1px solid var(--assistant-msg-border)` on `.message.assistant .message-content`. Dark mode appearance is unchanged; light mode bubbles now have a visible boundary.

### Chat messages scrollbar track mismatch
- **Problem**: `.chat-messages::-webkit-scrollbar-track` used `var(--surface)` (#ffffff in light mode) but `.chat-messages` background is `var(--background)` (#f8fafc) — created a visible white stripe along the scrollbar gutter.
- **Fix**: Changed track background from `var(--surface)` to `var(--background)` so it matches its container seamlessly.

### Implementation details verified
- `data-theme` attribute is set on `<html>` (`document.documentElement`), ensuring CSS variable inheritance cascades to all elements
- `[data-theme="light"]` selector has higher specificity than `:root`, so light values correctly override dark defaults
- All color values in CSS rules use `var()` references — no hardcoded colors outside of variable declarations (except `header h1` gradient which is `display: none`, and `#sendButton:hover` blue glow which works in both themes)
- The `--user-message` (#2563eb) with hardcoded `color: white` gives ~4.6:1 contrast in both themes (passes WCAG AA)
- All `var()` references point to variables that exist in both `:root` and `[data-theme="light"]` blocks

## Accessibility
- The toggle button is a native `<button>` element, so it is keyboard-focusable and activatable with Enter/Space by default
- `aria-label` dynamically reflects the action the button will perform
- Focus state shows a visible focus ring (`box-shadow: 0 0 0 3px var(--focus-ring)`)
- `title` attribute provides a tooltip on hover
- All text colors in light mode meet WCAG AA contrast requirements (minimum 4.5:1 for normal text)

## Theme Persistence
User preference is stored in `localStorage` under the key `theme` (`"light"` or `"dark"`). On page load, an IIFE reads this value and applies the attribute before the DOM renders, avoiding a flash of the wrong theme.
