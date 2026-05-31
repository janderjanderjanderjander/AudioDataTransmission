import os
import cv2
import sys
import scipy
import datetime
import numpy as np
import sounddevice as sd
import threading
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy
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

        self.inverted = True
        self.sendbinary = True
        self.debugging = False
        self.hamming = False
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
            self.calibBTND = QPushButton("Prev note")
            self.calibBTND.clicked.connect(lambda: self.calibrate(False))
            mainLayout.addWidget(self.calibBTND)


        else:
            filePath = "common/pics/test4.bmp"
            senderlayout = QVBoxLayout()

            imglayout = QHBoxLayout()
            
            self.image_frame = QLabel()
            self.image_frame.setFixedSize(300, 300)
            self.image_frame.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            imglayout.addWidget(self.image_frame)

            img2layout = QVBoxLayout()
            fileInputLabel = QLabel("Filepath: ")
            img2layout.addWidget(fileInputLabel)
            self.fileInput = QLineEdit()
            self.fileInput.setText(filePath)
            img2layout.addWidget(self.fileInput)

            self.changepicBTN = QPushButton("Change picture")
            self.changepicBTN.clicked.connect(self.picture_changed)
            img2layout.addWidget(self.changepicBTN)
            
            imglayout.addLayout(img2layout)
            senderlayout.addLayout(imglayout)

            self.image = cv2.imread(filePath, cv2.IMREAD_GRAYSCALE)
            print(self.image.shape)

            qimg = QImage(self.image.data, self.image.shape[1], self.image.shape[0], QImage.Format.Format_Grayscale8)
            self.image_frame.setPixmap(QPixmap.fromImage(qimg))

            self.canvasPixmap = QPixmap.fromImage(qimg)
            
            self.image_frame.setPixmap(
                self.canvasPixmap.scaled(
                    300,
                    300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
            )

            tonelayout = QHBoxLayout()
            toneInputLabel = QLabel("Tone length (ms)")
            tonelayout.addWidget(toneInputLabel)
            self.toneInput = QLineEdit()
            self.toneInput.setText(str(int(self.duration * 1000)))
            tonelayout.addWidget(self.toneInput)
            senderlayout.addLayout(tonelayout)
            
            self.toneInput.textChanged.connect(self.duration_changed)

            self.pictureBTN = QPushButton("Play picture")
            self.pictureBTN.setCheckable(True)
            self.pictureBTN.clicked.connect(self.sendPicture)
            senderlayout.addWidget(self.pictureBTN)
            mainLayout.addLayout(senderlayout)

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
        t = np.linspace(0, self.duration, int(self.sample_rate * self.duration), endpoint=False)
        self.audio = np.array([np.sin(2 * np.pi * f * t) for f in self.outputFreqs])

        binary_repr_v = np.vectorize(np.binary_repr)
        image_bitvector = ""

        if self.sendbinary:
            if self.inverted:
                temp = [1 if x != 0 else 0 for x in self.image.flatten()]
            else:
                temp = [1 if x == 0 else 0 for x in self.image.flatten()]
            image_bitvector = "".join(binary_repr_v(temp))
        else:
            image_bitvector = "".join(binary_repr_v(self.image.flatten(), 8))

        print(f"Saatimine võtab {str(datetime.timedelta(seconds=(np.ceil(len(image_bitvector) * 16/44) * self.duration)))}")

        counter = 0
        hcounter = 0
        output_audio = np.zeros(0)
        debugstring = ""

        stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1
        )
        stream.start()

        if self.debugging:
            idx = 0

            while True:
                if self.kill_send:
                    print("Stopping send!")
                    return
            
                bytearr = np.zeros(t.size)
                bytearr += self.audio[idx]
                idx += 1

                output_audio = np.append(output_audio, self.audio[-1][len(self.audio[-1])//2:])
                output_audio = np.append(output_audio, bytearr)

                if idx == 17:
                    sd.play(output_audio, self.sample_rate)
                    sd.wait()
                    idx = 0
                    output_audio = np.zeros(0)

        if self.hamming:
            n = 11
        else:
            n = 16

        for i in range(0, len(image_bitvector), n):
            if self.kill_send:
                print("Stopping send!")
                stream.stop()
                stream.close()
                return
            
            if self.hamming:
                raw = image_bitvector[i:i+11]
                debugstring += raw
                print(f"D: {raw.ljust(11, "0")}")
                data = [int(b) for b in raw.ljust(11, "0")]
                self.encodedBits = encodeHamming(data, self.dataPositions, self.parityPositions)
                encstr = ("".join(map(str, self.encodedBits))).ljust(16, "0")
            else:
                encstr = image_bitvector[i:i+16]
            
            print(f"H{hcounter}: {encstr}")
            hcounter += 1

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

                if (hcounter % 10 == 0):
                    print("Playing chunk!")
                    #scipy.io.wavfile.write("temp.wav", self.sample_rate, output_audio)
                    stream.write(output_audio.astype(np.float32))
                    output_audio = np.zeros(0)

        spacer = 8
        print("\n".join(debugstring[i:i+spacer] for i in range(0, len(debugstring), spacer)))

        stream.write(output_audio.astype(np.float32))

        while stream.active:
            if self.kill_send:
                print("Stopping send!")
                stream.stop()
                stream.close()
                return

        print("Image sent!")

    def duration_changed(self, text):
        if text != "":
            self.duration = int(text) / 1000
        else:
            self.duration = 0.12

    def picture_changed(self):
        filePath = self.fileInput.text()
        if not os.path.isfile(filePath):
            print("File does not exist!")
            return
        
        self.image = cv2.imread(filePath, cv2.IMREAD_GRAYSCALE)
        print(self.image.shape)

        qimg = QImage(self.image.data, self.image.shape[1], self.image.shape[0], QImage.Format.Format_Grayscale8)
        self.image_frame.setPixmap(QPixmap.fromImage(qimg))

        self.canvasPixmap = QPixmap.fromImage(qimg)
        
        self.image_frame.setPixmap(
            self.canvasPixmap.scaled(
                300,
                300,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
        )

    def calibrate(self, up):
        #check if were done
        if self.calibIndex >= len(self.outputFreqs):
            self.stop_tone()
            print("Calibration tones complete.")
            self.calibIndex = -1
        else:
            if up:
                self.calibBTNU.setText(f"Next note: {self.outputFreqs[self.calibIndex + 1]}")
                self.calibBTND.setText(f"Prev note: {self.outputFreqs[self.calibIndex]}")
                self.calibIndex += 1
            else:
                self.calibBTNU.setText(f"Next note: {self.outputFreqs[self.calibIndex]}")
                self.calibBTND.setText(f"Prev note: {self.outputFreqs[self.calibIndex - 1]}")
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
