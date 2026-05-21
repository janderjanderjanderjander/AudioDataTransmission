import os
import cv2
import sys
import scipy
import datetime
import numpy as np
import sounddevice as sd
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


class SenderWidget(QWidget):
    def __init__(self):
        super().__init__()

        #Debugging tools
        self.hammingDebug = 0
        self.calibration = 1

        self.setWindowTitle("Sender")

        self.sample_rate = 44100
        self.is_playing = False
        self.stream = None
        self.phase = 0.0
        self.image = None

        #Hamming
        self.parityPositions = {1, 2, 4, 8} 
        self.dataPositions = [p for p in range(1, 16) if p not in self.parityPositions]
        self.encodedBits = None 
        self.outputFreqs = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000]
        self.activeFreqs = []

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
            self.timer = QTimer()
            self.timer.timeout.connect(self.calibrate)
            self.calibIndex = 0

            self.calibBTN = QPushButton("Start playing - This need to be pressed at the same time as receiver")
            self.calibBTN.clicked.connect(self.startCalibration)
            mainLayout.addWidget(self.calibBTN)


        else:
            #TODO: Send pic
            '''
            Dimensions: 500x500, Channels: 3
            Bits per channel: 8
            Total bits: 6,000,000
            '''
            filePath = "common/pics/samplePicBlackNWhiteSmall.png"
            self.image = cv2.imread(filePath)


            toneInputLabel = QLabel("Tone length (ms)")
            mainLayout.addWidget(toneInputLabel)
            toneInput = QLineEdit()
            mainLayout.addWidget(self.toneInput)

            pauseInputLabel = QLabel("Pause length (ms)")
            mainLayout.addWidget(pauseInputLabel)
            pauseInput = QLineEdit()
            mainLayout.addWidget(self.pauseInput)

            preampleInputLabel = QLabel("Preample byte")
            mainLayout.addWidget(preampleInputLabel)
            preampleInput = QLineEdit()
            mainLayout.addWidget(self.preampleInput)

            self.pictureBTN = QPushButton("Play picture")
            self.pictureBTN.setCheckable(True)
            self.pictureBTN.clicked.connect(self.togglePicture)
            mainLayout.addWidget(self.pictureBTN)

        self.setLayout(mainLayout)

    def startCalibration(self):
        self.timer.start(100)

    def calibrate(self):
        #check if were done
        if self.calibIndex >= len(self.outputFreqs):
            self.timer.stop()
            self.stop_tone()
            print("Calibration tones complete.")
            self.calibIndex = 0
        else:
            freq = self.outputFreqs[self.calibIndex]
            self.start_tone(freq)
            self.calibIndex += 1
            self.timer.setInterval(200)


    def onEncode(self):
        raw = self.dataInput.text().strip()
 
        data = [int(b) for b in raw]
        self.encodedBits = self.encodeHamming(data)
        self.encodedLabel.setText("".join(str(b) for b in self.encodedBits))

    def togglePicture(self, checked):
        if checked:
            raw = self.image
            data = [int(b) for b in raw]
            self.encodedBits = self.encodeHamming(data)



        else:
            self.stop_tone()

    def toggleSymbol(self, checked):
        if checked:

            # Frequencies that have 1
            activeFreqs = []
            for i in range(0, 15):
                if self.encodedBits[i] == 1:
                    activeFreqs.append(self.outputFreqs[i])

            self.activeFreqs = activeFreqs
            self.phase = 0.0
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=self.generateSignal,
            )
            self.stream.start()
            self.is_playing = True
        else:
            self.stop_tone()


    def generateSignal(self, outdata, frames, time, status):
        t = (self.phase + np.arange(frames)) / self.sample_rate
        # Sum a sine wave for each active frequency, then normalise
        signal = sum(np.sin(2 * np.pi * f * t) for f in self.activeFreqs)
        signal = signal / max(len(self.activeFreqs), 1)   # prevent clipping
        outdata[:, 0] = signal.astype(np.float32)
        self.phase += frames

    def closeEvent(self, event):
        self.stop_tone()
        event.accept()

    def start_tone(self, freq):
        
        t = np.linspace(0, 1, self.sample_rate, endpoint=False)
        wave = np.sin(2 * np.pi * freq * t).astype(np.float32)
        
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32'
        )
        self.stream.start()
        self.stream.write(wave)

    def stop_tone(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_playing = False
        if self.hammingDebug == 1:
            self.symbolBTN.setChecked(False)
        
    def encodeHamming(self, data): 
        '''
        Turn 11 data bits into 15 bit hamming code.
        Includes 4 parity bits capable of repairing 1 error.
        '''
        product = [0] * 15
        for i, pos in enumerate(self.dataPositions): # Sets data bits into correct positions
            product[pos - 1] = data[i]

        for p in sorted(self.parityPositions):  # Go through each of the parity bit positions
            covered = []
            for pos in range(1, 16):        # pos = 1, 2, 3, ... 15
                if pos != p:                # skip the parity bit itself
                    if pos & p:             # anding check if the number is covered by the parity bit. 0 0 0 0 each digit has a master
                        covered.append(product[pos - 1])
            result = 0
            for bit in covered:
                result = result ^ bit       # XOR everything together
            product[p - 1] = result        # set the parity bit to the result

        return product


