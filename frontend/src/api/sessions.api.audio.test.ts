import { describe, expect, it, vi, beforeEach } from 'vitest'
import api from '@/api/client'
import { fetchAssistantAudioObjectUrl } from '@/api/sessions.api'
import { stubCreateObjectURL } from '@/test/urlBlobTestUtils'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
  },
}))

describe('fetchAssistantAudioObjectUrl', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
  })

  it('requests a blob and returns an object URL', async () => {
    const blob = new Blob(['x'], { type: 'audio/mpeg' })
    vi.mocked(api.get).mockResolvedValue({ data: blob })

    await stubCreateObjectURL('blob:mocked', async (created) => {
      const url = await fetchAssistantAudioObjectUrl('/v1/turns/3/audio')

      expect(api.get).toHaveBeenCalledWith('/v1/turns/3/audio', { responseType: 'blob' })
      expect(created).toEqual([blob])
      expect(url).toBe('blob:mocked')
    })
  })
})
