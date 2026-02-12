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
