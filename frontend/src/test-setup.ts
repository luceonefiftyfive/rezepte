import '@testing-library/jest-dom/vitest';

if (!globalThis.crypto?.randomUUID) {
  let counter = 0;
  Object.defineProperty(globalThis, 'crypto', {
    value: { randomUUID: () => `00000000-0000-4000-8000-${String(++counter).padStart(12, '0')}` },
  });
}
