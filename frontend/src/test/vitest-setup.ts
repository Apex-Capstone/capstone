/**
 * jsdom / Node `URL` may omit blob helpers; define spiable implementations for tests and app code.
 */
function ensureBlobUrlHelpers(): void {
  if (typeof URL.createObjectURL !== 'function') {
    Object.defineProperty(URL, 'createObjectURL', {
      value: function createObjectURL(blob: Blob) {
        return `blob:vitest-${blob.size}-${blob.type}`
      },
      writable: true,
      configurable: true,
    })
  }

  if (typeof URL.revokeObjectURL !== 'function') {
    Object.defineProperty(URL, 'revokeObjectURL', {
      value: function revokeObjectURL() {
        /* no-op in test env */
      },
      writable: true,
      configurable: true,
    })
  }
}

ensureBlobUrlHelpers()
