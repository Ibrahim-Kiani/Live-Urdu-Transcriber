"""Audio preprocessing utilities for translation."""

from __future__ import annotations

from io import BytesIO
from typing import Optional, Tuple
import wave
import warnings

warnings.filterwarnings("ignore", message=r"Numpy built with MINGW-W64.*")
warnings.filterwarnings("ignore", message=r"invalid value encountered in exp2")
warnings.filterwarnings("ignore", message=r"invalid value encountered in nextafter")
warnings.filterwarnings("ignore", message=r"invalid value encountered in log10")

import numpy as np


DEFAULT_SAMPLE_RATE = 16000
DEFAULT_NOISE_GATE_DB = -50.0
DEFAULT_COMPRESSOR_RATIO = 4.0
DEFAULT_COMPRESSOR_THRESHOLD_DB = -20.0
DEFAULT_TRIM_SILENCE_DB_OFFSET = 5.0


def _db_to_linear(db_value: float) -> float:
    return 10 ** (db_value / 20.0)


def _to_float32(audio: np.ndarray) -> np.ndarray:
    if audio.dtype == np.float32:
        return audio
    if np.issubdtype(audio.dtype, np.floating):
        return audio.astype(np.float32)
    if audio.dtype == np.int16:
        return (audio.astype(np.float32) / 32768.0).clip(-1.0, 1.0)
    if audio.dtype == np.int32:
        return (audio.astype(np.float32) / 2147483648.0).clip(-1.0, 1.0)
    if audio.dtype == np.uint8:
        return ((audio.astype(np.float32) - 128.0) / 128.0).clip(-1.0, 1.0)
    return audio.astype(np.float32)


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio
    return audio.mean(axis=1)


def _apply_noise_gate(audio: np.ndarray, threshold_db: float) -> np.ndarray:
    if audio.size == 0:
        return audio
    threshold = _db_to_linear(threshold_db)
    gated = audio.copy()
    gated[np.abs(gated) < threshold] = 0.0
    return gated


def _trim_dead_air(audio: np.ndarray, threshold_db: float) -> np.ndarray:
    if audio.size == 0:
        return audio
    threshold = _db_to_linear(threshold_db)
    indices = np.where(np.abs(audio) >= threshold)[0]
    if indices.size == 0:
        return np.array([], dtype=np.float32)
    start = indices[0]
    end = indices[-1] + 1
    return audio[start:end]


def _normalize_peak(audio: np.ndarray) -> np.ndarray:
    if audio.size == 0:
        return audio
    peak = np.max(np.abs(audio))
    if peak <= 0:
        return audio
    return (audio / peak).clip(-1.0, 1.0)


def _compress_dynamic_range(
    audio: np.ndarray,
    threshold_db: float,
    ratio: float,
) -> np.ndarray:
    if audio.size == 0:
        return audio
    threshold = _db_to_linear(threshold_db)
    abs_audio = np.abs(audio)
    over = abs_audio > threshold
    compressed = audio.copy()
    if np.any(over):
        compressed[over] = np.sign(audio[over]) * (
            threshold + (abs_audio[over] - threshold) / max(ratio, 1.0)
        )
    return compressed


def _resample(audio: np.ndarray, input_rate: int, target_rate: int) -> np.ndarray:
    if input_rate == target_rate or audio.size == 0:
        return audio
    duration = audio.size / float(input_rate)
    target_length = int(round(duration * target_rate))
    if target_length <= 1:
        return audio
    x_old = np.linspace(0, duration, num=audio.size, endpoint=False)
    x_new = np.linspace(0, duration, num=target_length, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def _read_wav_bytes(audio_bytes: bytes) -> Tuple[int, np.ndarray]:
    with wave.open(BytesIO(audio_bytes), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width == 1:
        dtype = np.uint8
    elif sample_width == 2:
        dtype = np.int16
    elif sample_width == 4:
        dtype = np.int32
    else:
        raise ValueError("Unsupported WAV sample width")

    audio = np.frombuffer(frames, dtype=dtype)
    if channels > 1:
        audio = audio.reshape(-1, channels)
    return sample_rate, audio


def _write_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    int16_audio = (audio * 32767.0).clip(-32768, 32767).astype(np.int16)
    output = BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int16_audio.tobytes())
    return output.getvalue()


def prepare_audio(
    audio_bytes: bytes,
    input_format: Optional[str] = None,
    noise_gate_db: float = DEFAULT_NOISE_GATE_DB,
    compressor_ratio: float = DEFAULT_COMPRESSOR_RATIO,
    compressor_threshold_db: float = DEFAULT_COMPRESSOR_THRESHOLD_DB,
) -> Optional[bytes]:
    if not audio_bytes:
        return None

    sample_rate, data = _read_wav_bytes(audio_bytes)
    audio = _ensure_mono(_to_float32(data))
    audio = _resample(audio, sample_rate, DEFAULT_SAMPLE_RATE)

    gated = _apply_noise_gate(audio, threshold_db=noise_gate_db)
    trimmed = _trim_dead_air(gated, threshold_db=noise_gate_db + DEFAULT_TRIM_SILENCE_DB_OFFSET)

    if trimmed.size == 0:
        return None

    normalized = _normalize_peak(trimmed)
    compressed = _compress_dynamic_range(
        normalized,
        threshold_db=compressor_threshold_db,
        ratio=compressor_ratio,
    )

    return _write_wav_bytes(compressed, DEFAULT_SAMPLE_RATE)
