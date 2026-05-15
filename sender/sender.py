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
    
import sys
import numpy as np
import sounddevice as sd

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
)


class SenderWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sender")

        self.sample_rate = 48000
        self.is_playing = False
        self.stream = None
        self.phase = 0.0

        self.layout = QVBoxLayout()

        label = QLabel("Sender")
        self.layout.addWidget(label)

        # Main layout only
        self.setLayout(self.layout)

        # Debug widgets are not created yet
        self.debug_created = False

    def create_debug_audio_controls(self):
        """
        Creates the debug tone generator UI.
        Call this only when needed.
        """

        if self.debug_created:
            return

        self.debug_created = True

        self.freq_label = QLabel("Frequency (Hz)")
        self.layout.addWidget(self.freq_label)

        self.freq_input = QLineEdit()
        self.freq_input.setPlaceholderText("1000")
        self.freq_input.setText("1000")
        self.layout.addWidget(self.freq_input)

        self.toggle_button = QPushButton("Start Tone")
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.toggle_tone)
        self.layout.addWidget(self.toggle_button)

    def audio_callback(self, outdata, frames, time, status):
        if status:
            print(status)

        try:
            freq = float(self.freq_input.text())
        except ValueError:
            freq = 1000.0

        t = (np.arange(frames) + self.phase) / self.sample_rate

        wave = 0.2 * np.sin(2 * np.pi * freq * t)

        outdata[:] = wave.reshape(-1, 1)

        self.phase += frames
        self.phase %= self.sample_rate

    def toggle_tone(self):
        if not self.is_playing:
            self.start_tone()
        else:
            self.stop_tone()

    def start_tone(self):
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self.audio_callback,
        )

        self.stream.start()

        self.is_playing = True
        self.toggle_button.setText("Stop Tone")

    def stop_tone(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self.is_playing = False
        self.toggle_button.setText("Start Tone")

    def closeEvent(self, event):
        self.stop_tone()
        event.accept()
















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


