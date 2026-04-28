import sounddevice as sd
import scipy
import numpy as np

sr = 44100
duration = 0.025

t = np.linspace(0, duration, int(sr * duration), endpoint=False)

fbyte = [110.0, 220.0, 440.0, 880.0, 1760.0, 3520.0, 7040.0, 14080.0]
audio = np.array([np.sin(2 * np.pi * f * t) for f in fbyte])

fgap = 678.0
audiogap = .5 * np.sin(2 * np.pi * fgap * t)

with open("projectDesc.png", "rb") as image:
    f = image.read()
    counter = 0
    totalaudio = np.zeros(0)

    for byte in bytearray(f):
        print("{:08b}".format(byte))
        bytearr = np.zeros(t.size)
        for bit in range(8):
            if ((byte >> bit) & 1):
                bytearr += audio[bit]

        totalaudio = np.append(totalaudio, (bytearr, audiogap))
        counter += 1

        if (counter % 200 == 0):
            print("Playing!")
            #scipy.io.wavfile.write("temp.wav", sr, totalaudio)
            sd.play(totalaudio, sr)
            sd.wait()
            totalaudio = np.zeros(0)