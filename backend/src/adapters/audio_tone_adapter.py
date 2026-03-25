"""Best-effort acoustic tone analysis for uploaded audio."""

from __future__ import annotations

import audioop
import math
import shutil
import subprocess
import tempfile
import wave
from array import array
from io import BytesIO
from pathlib import Path
from typing import Any

from config.logging import get_logger

logger = get_logger(__name__)


class AudioToneAdapter:
    """Extract coarse prosodic features and coaching-oriented tone labels."""

    provider_name = "prosody_v1"

    async def analyze_audio(
        self,
        audio_data: bytes,
        audio_format: str,
        transcript: str | None = None,
    ) -> dict[str, Any] | None:
        """Return structured tone metadata when the audio can be decoded."""
        try:
            wav_bytes = self._decode_to_wav(audio_data, audio_format)
            if not wav_bytes:
                return None

            pcm_data, sample_rate = self._load_pcm_mono_16bit(wav_bytes)
            if not pcm_data or sample_rate <= 0:
                return None

            return self._analyze_pcm(
                pcm_data=pcm_data,
                sample_rate=sample_rate,
                transcript=transcript,
            )
        except Exception as exc:
            logger.warning("Skipping audio tone analysis: %s", exc)
            return None

    def _decode_to_wav(self, audio_data: bytes, audio_format: str) -> bytes | None:
        """Decode arbitrary uploads to WAV when possible."""
        normalized_format = (audio_format or "").lower()
        if normalized_format == "wav":
            return audio_data

        ffmpeg_binary = shutil.which("ffmpeg")
        if not ffmpeg_binary:
            logger.info("ffmpeg not found; voice tone analysis is only available for wav uploads")
            return None

        with tempfile.NamedTemporaryFile(suffix=f".{normalized_format}", delete=False) as source_file:
            source_file.write(audio_data)
            source_path = Path(source_file.name)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as target_file:
            target_path = Path(target_file.name)

        try:
            completed = subprocess.run(
                [
                    ffmpeg_binary,
                    "-y",
                    "-i",
                    str(source_path),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(target_path),
                ],
                capture_output=True,
                check=False,
                timeout=20,
            )
            if completed.returncode != 0:
                logger.info("ffmpeg decode failed: %s", completed.stderr.decode(errors="ignore"))
                return None
            return target_path.read_bytes()
        finally:
            source_path.unlink(missing_ok=True)
            target_path.unlink(missing_ok=True)

    def _load_pcm_mono_16bit(self, wav_bytes: bytes) -> tuple[bytes, int]:
        """Normalize WAV content into mono 16-bit PCM for feature extraction."""
        with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            raw_frames = wav_file.readframes(wav_file.getnframes())

        pcm_data = raw_frames
        if channels > 1:
            pcm_data = audioop.tomono(pcm_data, sample_width, 0.5, 0.5)
        if sample_width != 2:
            pcm_data = audioop.lin2lin(pcm_data, sample_width, 2)
        return pcm_data, sample_rate

    def _analyze_pcm(
        self,
        pcm_data: bytes,
        sample_rate: int,
        transcript: str | None,
    ) -> dict[str, Any] | None:
        """Compute coarse prosody features from PCM samples."""
        sample_count = len(pcm_data) // 2
        if sample_count <= 0:
            return None

        duration_seconds = sample_count / sample_rate
        frame_samples = max(int(sample_rate * 0.03), 1)
        frame_bytes = frame_samples * 2
        if frame_bytes <= 0:
            return None

        rms_values: list[float] = []
        for start in range(0, len(pcm_data), frame_bytes):
            chunk = pcm_data[start : start + frame_bytes]
            if len(chunk) < frame_bytes // 2:
                continue
            rms_values.append(audioop.rms(chunk, 2) / 32768.0)

        if not rms_values:
            return None

        sorted_rms = sorted(rms_values)
        median_rms = sorted_rms[len(sorted_rms) // 2]
        peak_rms = max(rms_values)
        speech_threshold = max(0.015, median_rms * 1.8, peak_rms * 0.18)
        voiced_frames = [rms >= speech_threshold for rms in rms_values]
        voiced_seconds = sum(0.03 for voiced in voiced_frames if voiced)
        speech_ratio = min(1.0, voiced_seconds / duration_seconds) if duration_seconds > 0 else 0.0

        pause_count = self._count_pauses(voiced_frames)
        pauses_per_min = (pause_count / duration_seconds) * 60 if duration_seconds > 0 else 0.0

        avg_rms = sum(rms_values) / len(rms_values)
        volume_db = 20 * math.log10(max(avg_rms, 1e-5))

        pitch_hz = self._estimate_pitch_hz(pcm_data, sample_rate, voiced_frames, frame_samples)
        pace_wpm = self._estimate_pace_wpm(
            transcript=transcript,
            voiced_seconds=voiced_seconds,
            duration_seconds=duration_seconds,
        )

        clarity_score = self._clamp(0.55 * speech_ratio + 0.45 * (1.0 - min(pauses_per_min / 18.0, 1.0)))
        stability_score = self._clamp(0.6 * clarity_score + 0.4 * (1.0 - min(abs(volume_db + 18) / 20, 1.0)))
        pace_signal = min((pace_wpm or 0.0) / 220.0, 1.0)
        pitch_signal = min((pitch_hz or 140.0) / 260.0, 1.0)
        volume_signal = min(max((volume_db + 36.0) / 24.0, 0.0), 1.0)
        arousal = self._clamp(0.5 * volume_signal + 0.2 * pace_signal + 0.3 * pitch_signal)
        valence = self._clamp(0.5 * clarity_score + 0.3 * stability_score + 0.2 * (1.0 - arousal * 0.5))

        labels = self._classify_labels(
            arousal=arousal,
            clarity_score=clarity_score,
            stability_score=stability_score,
            pace_wpm=pace_wpm,
            speech_ratio=speech_ratio,
            pauses_per_min=pauses_per_min,
        )
        primary = labels[0] if labels else "neutral"
        secondary = labels[1] if len(labels) > 1 else None
        confidence = self._clamp(0.5 * speech_ratio + 0.3 * min(duration_seconds / 8.0, 1.0) + 0.2 * clarity_score)

        return {
            "primary": primary,
            "secondary": secondary,
            "confidence": round(confidence, 2),
            "dimensions": {
                "valence": round(valence, 2),
                "arousal": round(arousal, 2),
                "pace_wpm": round(pace_wpm, 1) if pace_wpm is not None else None,
                "volume_db": round(volume_db, 1),
                "pitch_hz": round(pitch_hz, 1) if pitch_hz is not None else None,
                "jitter": None,
                "shimmer": None,
                "pauses_per_min": round(pauses_per_min, 1),
            },
            "labels": labels,
            "provider": self.provider_name,
        }

    def _count_pauses(self, voiced_frames: list[bool]) -> int:
        """Count substantial silent gaps between voiced regions."""
        pauses = 0
        silence_run = 0
        for voiced in voiced_frames:
            if voiced:
                if silence_run >= 9:
                    pauses += 1
                silence_run = 0
                continue
            silence_run += 1
        return pauses

    def _estimate_pace_wpm(
        self,
        transcript: str | None,
        voiced_seconds: float,
        duration_seconds: float,
    ) -> float | None:
        """Estimate speaking pace from transcript length and voiced duration."""
        if not transcript or duration_seconds <= 0.5:
            return None
        word_count = len([word for word in transcript.split() if word.strip()])
        if word_count == 0:
            return None
        # Use a conservative denominator so VAD misses do not inflate pace labels.
        effective_speaking_seconds = max(voiced_seconds, duration_seconds * 0.7)
        if effective_speaking_seconds <= 0.5:
            return None
        return (word_count / effective_speaking_seconds) * 60.0

    def _estimate_pitch_hz(
        self,
        pcm_data: bytes,
        sample_rate: int,
        voiced_frames: list[bool],
        frame_samples: int,
    ) -> float | None:
        """Estimate pitch from the loudest voiced frame via autocorrelation."""
        best_frame_index = next((idx for idx, voiced in enumerate(voiced_frames) if voiced), None)
        if best_frame_index is None:
            return None

        start = best_frame_index * frame_samples * 2
        frame_bytes = pcm_data[start : start + (frame_samples * 2)]
        if len(frame_bytes) < frame_samples:
            return None

        samples = array("h")
        samples.frombytes(frame_bytes)
        if not samples:
            return None

        mean_value = sum(samples) / len(samples)
        normalized = [sample - mean_value for sample in samples]
        min_lag = max(int(sample_rate / 350), 1)
        max_lag = min(int(sample_rate / 80), len(normalized) // 2)
        if max_lag <= min_lag:
            return None

        best_lag = None
        best_score = 0.0
        for lag in range(min_lag, max_lag):
            score = 0.0
            for idx in range(len(normalized) - lag):
                score += normalized[idx] * normalized[idx + lag]
            if score > best_score:
                best_score = score
                best_lag = lag

        if not best_lag or best_score <= 0:
            return None
        return sample_rate / best_lag

    def _classify_labels(
        self,
        arousal: float,
        clarity_score: float,
        stability_score: float,
        pace_wpm: float | None,
        speech_ratio: float,
        pauses_per_min: float,
    ) -> list[str]:
        """Map acoustic features to coarse coaching labels."""
        labels: list[str] = []

        if arousal <= 0.35:
            labels.append("calm")
        elif arousal >= 0.72:
            labels.append("tense")

        if pace_wpm is not None:
            if pace_wpm >= 195:
                labels.append("hurried")
            elif pace_wpm <= 85:
                labels.append("hesitant")

        if clarity_score >= 0.63:
            labels.append("clear")
        # Be conservative with "unclear" because browser audio and lower-end mics
        # often reduce speech ratio without meaning the speaker was actually unclear.
        elif (
            clarity_score <= 0.22
            and speech_ratio <= 0.45
            and pauses_per_min >= 18
        ):
            labels.append("unclear")

        if stability_score >= 0.7:
            labels.append("steady")
        elif 0.4 <= arousal <= 0.68 and clarity_score >= 0.58:
            labels.append("confident")

        deduped: list[str] = []
        for label in labels:
            if label not in deduped:
                deduped.append(label)
        return deduped or ["neutral"]

    def _clamp(self, value: float, lower: float = 0.0, upper: float = 1.0) -> float:
        """Clamp numeric values to a bounded range."""
        return max(lower, min(upper, value))
