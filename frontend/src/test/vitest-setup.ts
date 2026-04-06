/**
 * jsdom does not implement blob URL helpers; polyfill so URL spies and app code work in tests.
 */
if (typeof URL.createObjectURL !== 'function') {
  URL.createObjectURL = function createObjectURL(blob: Blob) {
    return `blob:vitest-${blob.size}-${blob.type}`
  }
}

if (typeof URL.revokeObjectURL !== 'function') {
  URL.revokeObjectURL = function revokeObjectURL() {
    /* no-op in test env */
  }
}
