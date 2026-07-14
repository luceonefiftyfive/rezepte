# Installation

Requirements:

- Node.js 20 or newer
- npm 10 or newer

Recommended clean installation:

```bash
npm ci
npm test
npm run build
npm run dev
```

The `package-lock.json` uses only the public npm registry. If an older unpacked copy exists, remove `node_modules` before running `npm ci`.
