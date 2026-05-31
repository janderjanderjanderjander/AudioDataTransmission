import numpy as np
import sounddevice as sd
from .goertzel import goertzel

def getData(stream, chunkSize, sampleRate, freqGain, inputFreqs, option=0):
    samples, overflowed = stream.read(chunkSize)
    samples = samples.flatten()

    if overflowed:
        print("ERROR: Overflow")

    if option == 1:
        windowed = samples * np.hanning(len(samples))
        freqDom = np.fft.rfft(windowed)
        magnitudes = np.abs(freqDom) #magnitudes
        return magnitudes

    if option == 2:
        windowed = samples * np.hanning(len(samples))
        powers = np.array([goertzel(windowed, f, sampleRate, freqGain) for f in inputFreqs])
        mean = np.mean(powers)
        if mean > 0:
            powers = powers / mean 

        return powers

    return samples.flatten()

