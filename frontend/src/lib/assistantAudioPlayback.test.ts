import { describe, expect, it, vi } from 'vitest'
import { playAssistantAudioTrack, revokeAssistantAudioSession } from '@/lib/assistantAudioPlayback'
import {
  captureRevokeObjectURLCalls,
  captureRevokeObjectURLCallsAsync,
} from '@/test/urlBlobTestUtils'

describe('revokeAssistantAudioSession', () => {
  it('pauses audio and revokes the object URL', () => {
    const pause = vi.fn()
    const activeAudioRef = { current: { pause } as unknown as HTMLAudioElement }
    const activeObjectUrlRef = { current: 'blob:revoke-me' }

    const revoked = captureRevokeObjectURLCalls(() => {
      revokeAssistantAudioSession(activeAudioRef, activeObjectUrlRef)
    })

    expect(pause).toHaveBeenCalledOnce()
    expect(revoked).toEqual(['blob:revoke-me'])
    expect(activeAudioRef.current).toBeNull()
    expect(activeObjectUrlRef.current).toBeNull()
  })
})

describe('playAssistantAudioTrack', () => {
  it('fetches a blob URL, constructs audio, and plays', async () => {
    const activeAudioRef = { current: null as HTMLAudioElement | null }
    const activeObjectUrlRef = { current: null as string | null }
    const play = vi.fn().mockResolvedValue(undefined)
    const AudioCtor = vi.fn().mockImplementation(() => ({ play, onended: null as (() => void) | null }))

    await playAssistantAudioTrack('https://api.example/v1/turns/9/audio', {
      activeAudioRef,
      activeObjectUrlRef,
      fetchObjectUrl: vi.fn().mockResolvedValue('blob:fresh'),
      AudioCtor: AudioCtor as unknown as typeof Audio,
    })

    expect(AudioCtor).toHaveBeenCalledWith('blob:fresh')
    expect(play).toHaveBeenCalledOnce()
    expect(activeObjectUrlRef.current).toBe('blob:fresh')
  })

  it('revokes the previous object URL before a new clip', async () => {
    const activeAudioRef = { current: null as HTMLAudioElement | null }
    const activeObjectUrlRef = { current: 'blob:old' as string | null }
    const play = vi.fn().mockResolvedValue(undefined)
    const AudioCtor = vi.fn().mockImplementation(() => ({ play, onended: null as (() => void) | null }))

    const revoked = await captureRevokeObjectURLCallsAsync(async () => {
      await playAssistantAudioTrack('u', {
        activeAudioRef,
        activeObjectUrlRef,
        fetchObjectUrl: vi.fn().mockResolvedValue('blob:new'),
        AudioCtor: AudioCtor as unknown as typeof Audio,
      })
    })

    expect(revoked).toContain('blob:old')
    expect(activeObjectUrlRef.current).toBe('blob:new')
  })

  it('onended clears refs and revokes the clip URL', async () => {
    const activeAudioRef = { current: null as HTMLAudioElement | null }
    const activeObjectUrlRef = { current: null as string | null }
    const play = vi.fn().mockResolvedValue(undefined)
    let onended: (() => void) | null = null
    const AudioCtor = vi.fn().mockImplementation(() => ({
      play,
      get onended() {
        return onended
      },
      set onended(fn: (() => void) | null) {
        onended = fn
      },
    }))

    const revoked = await captureRevokeObjectURLCallsAsync(async () => {
      await playAssistantAudioTrack('u', {
        activeAudioRef,
        activeObjectUrlRef,
        fetchObjectUrl: vi.fn().mockResolvedValue('blob:on-ended'),
        AudioCtor: AudioCtor as unknown as typeof Audio,
      })
      expect(onended).toBeTypeOf('function')
      onended!()
    })

    expect(activeAudioRef.current).toBeNull()
    expect(activeObjectUrlRef.current).toBeNull()
    expect(revoked).toContain('blob:on-ended')
  })

  it('invokes onPlaybackEnded after teardown', async () => {
    const activeAudioRef = { current: null as HTMLAudioElement | null }
    const activeObjectUrlRef = { current: null as string | null }
    const play = vi.fn().mockResolvedValue(undefined)
    let onended: (() => void) | null = null
    const AudioCtor = vi.fn().mockImplementation(() => ({
      play,
      get onended() {
        return onended
      },
      set onended(fn: (() => void) | null) {
        onended = fn
      },
    }))
    const onPlaybackEnded = vi.fn()

    await captureRevokeObjectURLCallsAsync(async () => {
      await playAssistantAudioTrack('u', {
        activeAudioRef,
        activeObjectUrlRef,
        fetchObjectUrl: vi.fn().mockResolvedValue('blob:x'),
        AudioCtor: AudioCtor as unknown as typeof Audio,
        onPlaybackEnded,
      })
      onended!()
    })

    expect(onPlaybackEnded).toHaveBeenCalledOnce()
  })
})
