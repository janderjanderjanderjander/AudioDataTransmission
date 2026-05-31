import os
import cv2
import sys
import scipy
import datetime
import numpy as np
import sounddevice as sd
import threading
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
)
from lib.hamming import encodeHamming


class SenderWidget(QWidget):
    def __init__(self):
        super().__init__()

        #Debugging tools
        self.hammingDebug = 0
        self.calibration = 0

        self.setWindowTitle("Sender")

        self.freq_low = 1000
        self.freq_high = 15000
        self.freq_n = 17

        self.multiFSK = True
        self.sendbinary = True
        self.debugging = False
        self.kill_send = True

        self.sample_rate = 44100
        self.is_playing = False
        self.stream = None
        self.phase = 0.0
        self.image = None

        #Hamming
        self.parityPositions = {1, 2, 4, 8} 
        self.dataPositions = [p for p in range(1, 16) if p not in self.parityPositions]
        self.encodedBits = None 
        self.outputFreqs = np.round(np.linspace(self.freq_low, self.freq_high, self.freq_n))
        
        print(self.outputFreqs)
        self.activeFreqs = []

        self.duration = 0.12
        self.audio = np.array([])
        
        mainLayout = QVBoxLayout()
        mainLayout.setSpacing(10)
        label = QLabel("Sender")
        mainLayout.addWidget(label)

        if self.hammingDebug == 1:
            # INPUT
            InputLabel = QLabel("Enter 11 bits: ")
            mainLayout.addWidget(InputLabel)
    
            self.dataInput = QLineEdit()
            mainLayout.addWidget(self.dataInput)

            # Encode button
            self.encodeBTN = QPushButton("Encode (Hamming 15,11)")
            self.encodeBTN.clicked.connect(self.onEncode)
            mainLayout.addWidget(self.encodeBTN)

            # Encoded output
            encodedCode = QHBoxLayout()
            encodedCode.addWidget(QLabel("Encoded:"))
            self.encodedLabel = QLabel("Encoded")
            encodedCode.addWidget(self.encodedLabel)
            mainLayout.addLayout(encodedCode)

            # play button for encoded data
            self.symbolBTN = QPushButton("Play Symbol")
            self.symbolBTN.setCheckable(True)
            self.symbolBTN.clicked.connect(self.toggleSymbol)
            mainLayout.addWidget(self.symbolBTN)

        elif self.calibration == 1:
            self.calibIndex = 0

            self.calibBTNU = QPushButton("Next note")
            self.calibBTNU.clicked.connect(lambda: self.calibrate(True))
            mainLayout.addWidget(self.calibBTNU)
            self.calibBTND = QPushButton("Previous note")
            self.calibBTND.clicked.connect(lambda: self.calibrate(False))
            mainLayout.addWidget(self.calibBTND)


        else:
            #filePath = "common/pics/samplePicBlackNWhiteSmall.png"
            filePath = "common/pics/test.bmp"
            self.image = cv2.imread(filePath, cv2.IMREAD_GRAYSCALE)
            print(self.image.shape)

            toneInputLabel = QLabel("Tone length (ms)")
            mainLayout.addWidget(toneInputLabel)
            self.toneInput = QLineEdit()
            mainLayout.addWidget(self.toneInput)

            self.toneInput.textChanged.connect(self.duration_changed)

            self.pictureBTN = QPushButton("Play picture")
            self.pictureBTN.setCheckable(True)
            self.pictureBTN.clicked.connect(self.sendPicture)
            mainLayout.addWidget(self.pictureBTN)

        self.setLayout(mainLayout)

    def sendPicture(self, checked):
        if checked:
            self.kill_send = False

            threading.Thread(
                target=self.sendPictureWorker,
                daemon=True
            ).start()
        else:
            self.kill_send = True

    def sendPictureWorker(self):

        if self.debugging:
            send_debug = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
            self.debug(send_debug)
            return
    
        t = np.linspace(0, self.duration, int(self.sample_rate * self.duration), endpoint=False)
        self.audio = np.array([np.sin(2 * np.pi * f * t) for f in self.outputFreqs])

        binary_repr_v = np.vectorize(np.binary_repr)
        image_bitvector = ""

        if self.sendbinary:
            temp = [1 if x == 0 else 0 for x in self.image.flatten()]
            image_bitvector = "".join(binary_repr_v(temp))
        else:
            image_bitvector = "".join(binary_repr_v(self.image.flatten(), 8))
        
        print(f"Saatimine võtab {str(datetime.timedelta(seconds=(np.ceil(len(image_bitvector) * 16/44) * self.duration)))}")

        counter = 0
        output_audio = np.zeros(0)
        debugstring = ""

        for i in range(0, len(image_bitvector), 11):
            if self.kill_send:
                print("Stopping send!")
                return
            
            raw = image_bitvector[i:i+11]
            debugstring += raw
            print(f"D: {raw.ljust(11, "0")}")
            data = [int(b) for b in raw.ljust(11, "0")]
            self.encodedBits = encodeHamming(data, self.dataPositions, self.parityPositions)

            encstr = ("".join(map(str, self.encodedBits))).ljust(16, "0")
            print(f"H: {encstr}\n")

            for x in range(0, 16, 4):
                idx = int(encstr[x:x+4], 2)

                bytearr = np.zeros(t.size)
                bytearr += self.audio[idx]

                if counter == 0:
                    output_audio = np.append(output_audio, [self.audio[-1], self.audio[-1], self.audio[-1], self.audio[-1]])
                else:
                    output_audio = np.append(output_audio, self.audio[-1][len(self.audio[-1])//2:])
                
                output_audio = np.append(output_audio, bytearr)

                counter += 1

                if (counter % 200 == 0):
                    print("Playing chunk!")
                    #scipy.io.wavfile.write("temp.wav", self.sample_rate, output_audio)
                    sd.play(output_audio, self.sample_rate)
                    sd.wait()
                    output_audio = np.zeros(0)
                    input()

        spacer = 8
        print("\n".join(debugstring[i:i+spacer] for i in range(0, len(debugstring), spacer)))

        sd.play(output_audio, self.sample_rate)
        sd.wait()
        output_audio = np.zeros(0)
        
        print("Image sent!")

    def duration_changed(self, text):
        if text != "":
            self.duration = int(text) / 1000
        else:
            self.duration = 0.12

    def calibrate(self, up):
        #check if were done
        if self.calibIndex >= len(self.outputFreqs):
            self.stop_tone()
            print("Calibration tones complete.")
            self.calibIndex = 0
        else:
            if up:
                self.calibIndex += 1
            else:
                self.calibIndex -= 1

            activeFreqs = []

            activeFreqs.append(self.outputFreqs[self.calibIndex])
            self.start_tone(activeFreqs)   

    def onEncode(self):
        raw = self.dataInput.text().strip()
 
        data = [int(b) for b in raw]
        self.encodedBits = self.encodeHamming(data)
        self.encodedLabel.setText("".join(str(b) for b in self.encodedBits))

    def debug(self, input_bits):
        activeFreqs = []

        for i in range(len(input_bits)):
            if input_bits[i] == 1:
                activeFreqs.append(self.outputFreqs[i])

        self.start_tone(activeFreqs)

    def toggleSymbol(self, checked):
        activeFreqs = []

        if checked:
            for i in range(0, 15):
                if self.encodedBits[i] == 1:
                    activeFreqs.append(self.outputFreqs[i])

            self.start_tone(activeFreqs)
        else:
            self.stop_tone()

    def start_tone(self, freq):
        self.stop_tone()
        
        self.activeFreqs = freq
        
        def callback(outdata, frames, time, status):
            t = (self.phase + np.arange(frames)) / self.sample_rate
            signal = sum(np.sin(2 * np.pi * f * t) for f in self.activeFreqs)
            signal /= np.max(np.abs(signal))   #normalize
            outdata[:, 0] = signal.astype(np.float32)
            self.phase += frames

        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=callback
        )
        self.stream.start()

    def stop_tone(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_playing = False
        if self.hammingDebug == 1:
            self.symbolBTN.setChecked(False)

    def closeEvent(self, event):
        self.stop_tone()
        event.accept()
