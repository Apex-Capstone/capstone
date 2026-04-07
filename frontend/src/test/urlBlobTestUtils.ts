/**
 * Vitest cannot always `vi.spyOn(URL, 'revokeObjectURL')` in jsdom/Node; patch with defineProperty instead.
 */

export function captureRevokeObjectURLCalls(run: () => void): string[] {
  const calls: string[] = []
  const previous = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL')
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    writable: true,
    value: (u: string) => {
      calls.push(u)
    },
  })
  try {
    run()
  } finally {
    if (previous) {
      Object.defineProperty(URL, 'revokeObjectURL', previous)
    } else {
      Reflect.deleteProperty(URL, 'revokeObjectURL')
    }
  }
  return calls
}

export async function captureRevokeObjectURLCallsAsync(run: () => Promise<void>): Promise<string[]> {
  const calls: string[] = []
  const previous = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL')
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    writable: true,
    value: (u: string) => {
      calls.push(u)
    },
  })
  try {
    await run()
  } finally {
    if (previous) {
      Object.defineProperty(URL, 'revokeObjectURL', previous)
    } else {
      Reflect.deleteProperty(URL, 'revokeObjectURL')
    }
  }
  return calls
}

export async function stubCreateObjectURL<T>(
  returnUrl: string,
  run: (created: Blob[]) => Promise<T>,
): Promise<T> {
  const created: Blob[] = []
  const previous = Object.getOwnPropertyDescriptor(URL, 'createObjectURL')
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    writable: true,
    value: (blob: Blob) => {
      created.push(blob)
      return returnUrl
    },
  })
  try {
    return await run(created)
  } finally {
    if (previous) {
      Object.defineProperty(URL, 'createObjectURL', previous)
    } else {
      Reflect.deleteProperty(URL, 'createObjectURL')
    }
  }
}
