import sounddevice as sd
import scipy
import numpy as np
import os
import datetime
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout


class SenderWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        label = QLabel("Sender")
        layout.addWidget(label)

        self.setLayout(layout)
    
    def freq_keying(filepath):
        sr = 48000
        duration = 0.3

        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        start = 1000.0 #Madalaim sagedus
        delta = 100.0 #Kahe sageduse vahe
        n = 9          #Mitu sageduskomponenti me lisame (9-s on nö clock)

        inputFreqs = start + delta * np.arange(n)
        audio = np.array([np.sin(2 * np.pi * f * t) for f in inputFreqs])

        gap = np.zeros(int(sr * duration))
        filepath = "/home/jander/School/DSP/projectDSP/common/pics/samplePicBlackNWhiteSmall.png"

        with open(filepath, "rb") as file:
            f = file.read()

            print(f"Saatimine võtab {str(datetime.timedelta(seconds=duration*os.path.getsize(filepath)))}")
            input("Vajuta jätkamiseks...")
            
            counter = 0

            totalaudio = np.zeros(0)

            for byte in bytearray(f):
                print("{:08b}".format(byte))
                
                bytearr = np.zeros(t.size)
                for bit in range(8):
                    if ((byte >> bit) & 1):
                        bytearr += audio[bit]

                #TODO: fix parity bit
                #right now it just does  0 1 0 1 0 1 and receiver checks it.
                if counter % 2 == 0:
                    bytearr += audio[-1]
                
                totalaudio = np.append(totalaudio, bytearr)
                #totalaudio = np.append(totalaudio, gap)
                
                counter += 1

                if (counter % 1000 == 0):
                    print("Playing!")
                    scipy.io.wavfile.write("temp.wav", sr, totalaudio)
                    break
                    sd.play(totalaudio, sr)
                    sd.wait()
                    totalaudio = np.zeros(0)

        print("End of file!")
        scipy.io.wavfile.write("temp.wav", sr, totalaudio)


