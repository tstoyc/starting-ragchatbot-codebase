# Frontend Code Quality Tools

## What was added

### New files

- **`frontend/package.json`** - Node project config with dev dependencies (Prettier 3.x, ESLint 8.x) and npm scripts: `format`, `format:check`, `lint`, `lint:fix`, `quality`
- **`frontend/.prettierrc`** - Prettier config: 2-space indent, single quotes, no trailing commas, 100 char print width
- **`frontend/.eslintrc.json`** - ESLint config: browser globals, `marked` as a CDN global, rules for `eqeqeq` (error), `curly` (error), `no-unused-vars` (warn), `no-console` (off)
- **`frontend/format-check.sh`** - Shell script that runs both Prettier check and ESLint in one command; works from any directory

### Modified files

- **`frontend/index.html`** - Reformatted by Prettier (2-space indent, self-closing tags, attribute formatting)
- **`frontend/script.js`** - Reformatted by Prettier (2-space indent, trailing comma removal) + ESLint auto-fixed 4 `curly` violations (added braces to single-line `if` statements)
- **`frontend/style.css`** - Reformatted by Prettier (2-space indent, selector-per-line)
- **`.gitignore`** - Added `node_modules/` entry

## Usage

```bash
cd frontend

# Install dependencies
npm install

# Format all files
npm run format

# Check formatting without writing
npm run format:check

# Lint JavaScript
npm run lint

# Lint and auto-fix
npm run lint:fix

# Run all checks (format check + lint)
npm run quality

# Or use the shell script (works from any directory)
./format-check.sh
```

---

# Frontend Changes: Dark/Light Theme Toggle

## Overview
Added a dark/light mode toggle button to the UI, positioned in the top-right corner with sun/moon icons and smooth transition animations.

## Files Modified

### `frontend/index.html`
- Added a `<button>` element with id `themeToggle` right after the `<body>` tag
- The button contains two inline SVG icons: a sun (visible in dark mode) and a moon (visible in light mode)
- Includes `aria-label` and `title` attributes for accessibility
- Bumped cache-bust versions for `style.css` and `script.js`

### `frontend/style.css`
- **Light theme CSS variables**: Added a `[data-theme="light"]` selector with light-mode color values
- **`--code-bg` variable**: Introduced a new CSS variable for code block backgrounds
- **No-transitions guard**: Added `.no-transitions` class rule to prevent flash on load
- **Theme transition rule**: Smooth 0.3s transitions on all theme-sensitive elements
- **Toggle button styles**: Fixed positioning, icon crossfade animation

### `frontend/script.js`
- **Early theme application (IIFE)**: Reads localStorage/OS preference before DOM renders
- **`initThemeToggle()`**: Re-enables transitions, registers click + OS preference listeners
- **`applyTheme(theme)`**: Sets/removes `data-theme` attribute
- **`updateToggleAriaLabel()`**: Dynamic aria-label updates

## Accessibility
- Native `<button>` element, keyboard-focusable
- Dynamic `aria-label` and visible focus ring
- All light mode text colors meet WCAG AA contrast requirements

## Theme Persistence
User preference stored in `localStorage` under key `theme`.
