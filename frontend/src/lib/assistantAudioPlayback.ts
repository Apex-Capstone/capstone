/**
 * Assistant TTS playback: blob URL fetch, HTMLAudioElement lifecycle, revocation.
 */

export function revokeAssistantAudioSession(
  activeAudioRef: { current: HTMLAudioElement | null },
  activeObjectUrlRef: { current: string | null },
): void {
  activeAudioRef.current?.pause()
  activeAudioRef.current = null
  if (activeObjectUrlRef.current) {
    URL.revokeObjectURL(activeObjectUrlRef.current)
    activeObjectUrlRef.current = null
  }
}

export type PlayAssistantAudioContext = {
  activeAudioRef: { current: HTMLAudioElement | null }
  activeObjectUrlRef: { current: string | null }
  fetchObjectUrl: (audioUrl: string) => Promise<string>
  AudioCtor?: typeof Audio
  /** Called after the clip ends and its object URL is revoked (e.g. resume conversation mode). */
  onPlaybackEnded?: () => void
}

/**
 * Stops any current clip, fetches a new object URL, plays it, and revokes on end.
 */
export async function playAssistantAudioTrack(
  audioUrl: string,
  ctx: PlayAssistantAudioContext,
): Promise<void> {
  const Ctor = ctx.AudioCtor ?? globalThis.Audio

  revokeAssistantAudioSession(ctx.activeAudioRef, ctx.activeObjectUrlRef)

  const objectUrl = await ctx.fetchObjectUrl(audioUrl)
  ctx.activeObjectUrlRef.current = objectUrl

  const audio = new Ctor(objectUrl) as HTMLAudioElement
  ctx.activeAudioRef.current = audio

  audio.onended = () => {
    if (ctx.activeAudioRef.current === audio) {
      ctx.activeAudioRef.current = null
    }
    if (ctx.activeObjectUrlRef.current === objectUrl) {
      URL.revokeObjectURL(objectUrl)
      ctx.activeObjectUrlRef.current = null
    }
    ctx.onPlaybackEnded?.()
  }

  await audio.play()
}
