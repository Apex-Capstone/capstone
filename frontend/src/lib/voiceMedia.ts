/**
 * Browser voice capture helpers (MIME types, eligibility, post-record checks).
 */

export const AUDIO_EXTENSION_BY_MIME_TYPE: Record<string, string> = {
  'audio/webm;codecs=opus': 'webm',
  'audio/webm': 'webm',
  'audio/ogg;codecs=opus': 'ogg',
  'audio/ogg': 'ogg',
  'audio/mp4': 'm4a',
  'audio/x-m4a': 'm4a',
  'audio/mpeg': 'mp3',
  'audio/mp3': 'mp3',
  'audio/wav': 'wav',
  'audio/x-wav': 'wav',
}

export const PREFERRED_RECORDING_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
] as const

export const VOICE_ACTIVITY_RMS_THRESHOLD = 0.02
export const MIN_VOICE_ACTIVE_FRAMES = 5

export function getPreferredRecordingMimeType(
  isTypeSupported: (mimeType: string) => boolean,
  preferredList: readonly string[] = PREFERRED_RECORDING_MIME_TYPES,
): string {
  return preferredList.find((mimeType) => isTypeSupported(mimeType)) ?? ''
}

export function getRecordingFileExtension(mimeType: string): string {
  return AUDIO_EXTENSION_BY_MIME_TYPE[mimeType.toLowerCase()] ?? 'webm'
}

export type VoiceRecordingEnv = {
  navigator?: Navigator
  MediaRecorder?: typeof MediaRecorder
}

/**
 * Whether the runtime exposes APIs needed for microphone recording.
 */
export function isBrowserVoiceRecordingSupported(env?: VoiceRecordingEnv): boolean {
  const nav = env?.navigator ?? (typeof navigator !== 'undefined' ? navigator : undefined)
  const MR = env?.MediaRecorder ?? (typeof MediaRecorder !== 'undefined' ? MediaRecorder : undefined)
  if (!nav?.mediaDevices?.getUserMedia) return false
  if (!MR) return false
  return true
}

export type VoiceCaptureUploadDecision =
  | { upload: true }
  | { upload: false; reason: 'empty_blob' | 'no_speech_detected' }

/**
 * Mirrors the post-stop checks before uploading a recorded voice clip.
 */
export function evaluateVoiceCaptureForUpload(params: {
  blobByteSize: number
  maxRms: number
  activeFrames: number
  recordingDurationMs: number
  rmsThreshold?: number
  minActiveFrames?: number
}): VoiceCaptureUploadDecision {
  const {
    blobByteSize,
    maxRms,
    activeFrames,
    recordingDurationMs,
    rmsThreshold = VOICE_ACTIVITY_RMS_THRESHOLD,
    minActiveFrames = MIN_VOICE_ACTIVE_FRAMES,
  } = params

  if (blobByteSize === 0) {
    return { upload: false, reason: 'empty_blob' }
  }

  const detectedSpeech =
    maxRms >= rmsThreshold && activeFrames >= minActiveFrames && recordingDurationMs > 0

  if (!detectedSpeech) {
    return { upload: false, reason: 'no_speech_detected' }
  }

  return { upload: true }
}
