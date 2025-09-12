# d:\Smart Ambulance Traffic\core\audio.py

import collections
import sounddevice as sd
from scipy.fft import fft
import numpy as np
import constants

def audio_listener_thread(siren_detected_callback, stop_event=None):
    """
    Listens for siren sounds in a background thread and triggers a callback.

    Args:
        siren_detected_callback: A function to call when a siren is confirmed.
        stop_event (threading.Event, optional): Event to signal the thread to stop.
    """
    SAMPLE_RATE = 44100
    CHUNK_SIZE = 1024
    detection_history = collections.deque(maxlen=constants.SIREN_DETECTION_WINDOW)

    def audio_callback(indata, frames, time, status):
        if status: print(status, flush=True)
        yf = fft(indata[:, 0])
        xf = np.fft.fftfreq(CHUNK_SIZE, 1 / SAMPLE_RATE)
        peak_index = np.argmax(np.abs(yf))
        peak_frequency = abs(xf[peak_index])
        peak_magnitude = np.abs(yf[peak_index])

        is_siren_like = (
            constants.SIREN_FREQUENCY_RANGE[0] < peak_frequency < constants.SIREN_FREQUENCY_RANGE[1] and
            peak_magnitude > constants.SIREN_LOUDNESS_THRESHOLD
        )
        detection_history.append(is_siren_like)

        if sum(detection_history) >= constants.SIREN_CONFIRMATION_COUNT:
            siren_detected_callback()
            detection_history.clear()

    print("🎤 Starting audio listener...")
    with sd.InputStream(callback=audio_callback, channels=1, samplerate=SAMPLE_RATE, blocksize=CHUNK_SIZE):
        while not (stop_event and stop_event.is_set()):
            sd.sleep(1000)