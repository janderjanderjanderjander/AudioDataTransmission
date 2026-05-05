import sounddevice as sd
import scipy
import numpy as np
import os
import datetime

def qam(filepath):
    with open(filepath, "rb") as file:
        f = file.read()

        b_startf = 2000.0
        f_carr = 1000.0
        
        duration = 0.1
        sr = 44100

        totalaudio = np.zeros(0)
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        b_start = np.cos(2 * np.pi * b_startf * t)

        lut = [(1, np.pi/4), (1, 3*np.pi/4), (1, -np.pi/4), (1, -3*np.pi/4)]
        
        for byte in bytearray(f):
            print("{:08b}".format(byte))
            
            for bit2 in range(0, 8, 2):
                n = (byte >> bit2) & 0b11

                if bit2 == 0:
                    totalaudio = np.append(totalaudio, (lut[n][0] * np.cos((2 * np.pi * f_carr * t) + lut[n][1])) + b_start)
                else:
                    totalaudio = np.append(totalaudio, lut[n][0] * np.cos((2 * np.pi * f_carr * t) + lut[n][1]))
        
        scipy.io.wavfile.write("temp.wav", sr, totalaudio)
    

def freq_keying(filepath):
    sr = 48000
    duration = 0.5

    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    start = 1000.0
    delta = 1000.0
    n = 9

    fbyte = start + delta * np.arange(n)
    audio = np.array([np.sin(2 * np.pi * f * t) for f in fbyte])

    with open(filepath, "rb") as file:
        f = file.read()

        print(f"Saatimine võtab {str(datetime.timedelta(seconds=duration*os.path.getsize(filepath)))}")
        input("Vajuta jätkamiseks...")
        counter = 0
        rsyc_counter = 0

        resync_interval = 100

        totalaudio = np.zeros(0)

        for byte in bytearray(f):
            #print("{:08b}".format(byte))
            
            bytearr = np.zeros(t.size)
            for bit in range(8):
                if ((byte >> bit) & 1):
                    bytearr += audio[bit]
            
            if (rsyc_counter == resync_interval):
                bytearr += audio[-1]
                rsyc_counter = 0

            totalaudio = np.append(totalaudio, bytearr)
            counter += 1
            rsyc_counter += 1

            if (counter % 1000 == 0):
                print("Playing!")
                scipy.io.wavfile.write("temp.wav", sr, totalaudio)
                break
                sd.play(totalaudio, sr)
                sd.wait()
                totalaudio = np.zeros(0)

    print("End of file!")
    scipy.io.wavfile.write("temp.wav", sr, totalaudio)


def freq_sequenceDEBUG(filepath="temp.wav"):
    sr = 48000
    duration = 5.0  # seconds per tone

    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    start = 1000
    stop = 9000
    step = 1000

    frequencies = np.arange(start, stop + step, step)

    audio_sequence = []

    for f in frequencies:
        tone = np.sin(2 * np.pi * f * t)
        audio_sequence.append(tone)

    # Concatenate all tones into one long signal
    total_audio = np.concatenate(audio_sequence)

    # Normalize to avoid clipping
    total_audio = total_audio / np.max(np.abs(total_audio))

    # Convert to 16-bit PCM
    total_audio = (total_audio * 32767).astype(np.int16)

    scipy.io.wavfile.write(filepath, sr, total_audio)

    print("Written to temp.wav")

freq_sequenceDEBUG()
#freq_keying("common/pics/samplePicBlackNWhiteSmall.png")
#qam("projectDesc.png")