import { describe, expect, it } from 'vitest'
import {
  evaluateVoiceCaptureForUpload,
  getPreferredRecordingMimeType,
  getRecordingFileExtension,
  isBrowserVoiceRecordingSupported,
  PREFERRED_RECORDING_MIME_TYPES,
  VOICE_ACTIVITY_RMS_THRESHOLD,
} from '@/lib/voiceMedia'

describe('getPreferredRecordingMimeType', () => {
  it('returns first supported MIME from the default list', () => {
    const supported = new Set(['audio/webm', 'audio/mp4'])
    const mime = getPreferredRecordingMimeType((m) => supported.has(m))
    expect(mime).toBe('audio/webm')
  })

  it('returns empty string when nothing is supported', () => {
    expect(getPreferredRecordingMimeType(() => false)).toBe('')
  })

  it('respects a custom preference order', () => {
    const mime = getPreferredRecordingMimeType((m) => m === 'audio/ogg', ['audio/ogg', 'audio/webm'])
    expect(mime).toBe('audio/ogg')
  })
})

describe('getRecordingFileExtension', () => {
  it('maps known MIME types', () => {
    expect(getRecordingFileExtension('audio/webm;codecs=opus')).toBe('webm')
    expect(getRecordingFileExtension('audio/MPEG')).toBe('mp3')
  })

  it('defaults to webm for unknown types', () => {
    expect(getRecordingFileExtension('audio/unknown')).toBe('webm')
  })
})

describe('isBrowserVoiceRecordingSupported', () => {
  it('is false without getUserMedia', () => {
    const nav = { mediaDevices: {} } as Navigator
    class MR {}
    expect(isBrowserVoiceRecordingSupported({ navigator: nav, MediaRecorder: MR as typeof MediaRecorder })).toBe(
      false,
    )
  })

  it('is false without MediaRecorder', () => {
    const nav = {
      mediaDevices: { getUserMedia: async () => new MediaStream() },
    } as unknown as Navigator
    expect(isBrowserVoiceRecordingSupported({ navigator: nav, MediaRecorder: undefined })).toBe(false)
  })

  it('is true when both APIs exist', () => {
    const nav = {
      mediaDevices: { getUserMedia: async () => new MediaStream() },
    } as unknown as Navigator
    class MR {
      static isTypeSupported() {
        return true
      }
    }
    expect(isBrowserVoiceRecordingSupported({ navigator: nav, MediaRecorder: MR as unknown as typeof MediaRecorder })).toBe(
      true,
    )
  })
})

describe('evaluateVoiceCaptureForUpload', () => {
  it('rejects empty blobs', () => {
    expect(
      evaluateVoiceCaptureForUpload({
        blobByteSize: 0,
        maxRms: 1,
        activeFrames: 99,
        recordingDurationMs: 1000,
      }),
    ).toEqual({ upload: false, reason: 'empty_blob' })
  })

  it('rejects when voice activity is below threshold', () => {
    expect(
      evaluateVoiceCaptureForUpload({
        blobByteSize: 100,
        maxRms: VOICE_ACTIVITY_RMS_THRESHOLD / 2,
        activeFrames: 10,
        recordingDurationMs: 500,
      }),
    ).toEqual({ upload: false, reason: 'no_speech_detected' })
  })

  it('rejects when not enough active frames', () => {
    expect(
      evaluateVoiceCaptureForUpload({
        blobByteSize: 100,
        maxRms: VOICE_ACTIVITY_RMS_THRESHOLD,
        activeFrames: 2,
        recordingDurationMs: 500,
      }),
    ).toEqual({ upload: false, reason: 'no_speech_detected' })
  })

  it('rejects when duration is zero', () => {
    expect(
      evaluateVoiceCaptureForUpload({
        blobByteSize: 100,
        maxRms: 1,
        activeFrames: 10,
        recordingDurationMs: 0,
      }),
    ).toEqual({ upload: false, reason: 'no_speech_detected' })
  })

  it('accepts when RMS, frames, and duration pass', () => {
    expect(
      evaluateVoiceCaptureForUpload({
        blobByteSize: 500,
        maxRms: VOICE_ACTIVITY_RMS_THRESHOLD,
        activeFrames: 5,
        recordingDurationMs: 100,
      }),
    ).toEqual({ upload: true })
  })
})

describe('PREFERRED_RECORDING_MIME_TYPES', () => {
  it('lists webm first for broad browser support', () => {
    expect(PREFERRED_RECORDING_MIME_TYPES[0]).toContain('webm')
  })
})
