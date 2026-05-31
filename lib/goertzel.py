import numpy as np
   
# https://every-algorithm.github.io/2025/06/25/goertzel_algorithm.html
def goertzel(samples, target_freq, sample_rate, freqGain):
    """
    Compute the magnitude of the frequency component at target_freq
    in the given samples using the Goertzel algorithm.
    """
    N = len(samples)
    k = int(0.5 + (N * target_freq / sample_rate))
    omega = 2.0 * np.pi * k / N
    coeff = 2.0 * np.cos(omega)
    s_prev = 0.0
    s_prev2 = 0.0
    for sample in samples:
        s = sample + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s
    power = s_prev2**2 + s_prev**2 - coeff * s_prev * s_prev2
    magnitude = np.sqrt(power)

    adjustedMagnitude = magnitude * freqGain.get(target_freq, 1.0)

    return adjustedMagnitude