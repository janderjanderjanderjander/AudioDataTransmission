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
        self.calibration = 0

        self.setWindowTitle("Sender")

        self.freq_low = 1000
        self.freq_high = 15000
        self.freq_n = 17

        self.multiFSK = True
        self.sendbinary = True
        self.debugging = False

        self.sample_rate = 44100
        self.is_playing = False
        self.stream = None
        self.phase = 0.0
        self.image = None

        #Hamming
        self.parityPositions = {1, 2, 4, 8} 
        self.dataPositions = [p for p in range(1, 16) if p not in self.parityPositions]
        self.encodedBits = None 
        self.outputFreqs = np.round(np.linspace(1000, 15000, 17))
        #self.outputFreqs = np.round(np.logspace(np.log10(2000), np.log10(4000), self.freq_n))
        print(self.outputFreqs)
        self.activeFreqs = []

        self.duration = 0.2
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

            self.calibBTN = QPushButton("Next note")
            self.calibBTN.clicked.connect(self.calibrate)
            mainLayout.addWidget(self.calibBTN)


        else:
            #TODO: Send pic
            '''
            Dimensions: 500x500, Channels: 3
            Bits per channel: 8
            Total bits: 6,000,000
            '''
            #filePath = "common/pics/samplePicBlackNWhiteSmall.png"
            filePath = "common/pics/test3.bmp"
            self.image = cv2.imread(filePath, cv2.IMREAD_GRAYSCALE)
            print(self.image.shape)

            toneInputLabel = QLabel("Tone length (ms)")
            mainLayout.addWidget(toneInputLabel)
            self.toneInput = QLineEdit()
            mainLayout.addWidget(self.toneInput)

            self.toneInput.textChanged.connect(self.duration_changed)

            """
            pauseInputLabel = QLabel("Pause length (ms)")
            mainLayout.addWidget(pauseInputLabel)
            self.pauseInput = QLineEdit()
            mainLayout.addWidget(self.pauseInput)
            
            preampleInputLabel = QLabel("Preample byte")
            mainLayout.addWidget(preampleInputLabel)
            self.preampleInput = QLineEdit()
            mainLayout.addWidget(self.preampleInput)
            """

            self.pictureBTN = QPushButton("Play picture")
            self.pictureBTN.setCheckable(True)
            self.pictureBTN.clicked.connect(self.togglePicture)
            mainLayout.addWidget(self.pictureBTN)

        self.setLayout(mainLayout)

    def calibrate(self):
        #check if were done
        if self.calibIndex >= len(self.outputFreqs):
            self.stop_tone()
            print("Calibration tones complete.")
            self.calibIndex = 0
        else:
            freq = self.outputFreqs[self.calibIndex]
            self.start_tone(freq)
            self.calibIndex += 1

    def onEncode(self):
        raw = self.dataInput.text().strip()
 
        data = [int(b) for b in raw]
        self.encodedBits = self.encodeHamming(data)
        self.encodedLabel.setText("".join(str(b) for b in self.encodedBits))

    def debug(self, input_bits):
        # Frequencies that have 1
        activeFreqs = []
        for i in range(len(input_bits)):
            if input_bits[i] == 1:
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

    def togglePicture(self, checked):
        if checked:
            if self.debugging:
                send_debug = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
                self.debug(send_debug)
                return

            if len(self.image.shape) > 2:
                print(f"Saatimine võtab {str(datetime.timedelta(seconds=((self.image.shape[0] * self.image.shape[1] * self.image.shape[2]) * 2 * self.duration)))}")
            else:
                print(f"Saatimine võtab {str(datetime.timedelta(seconds=((self.image.shape[0] * self.image.shape[1]) * 4 * self.duration)))}")
            
            #print(len(self.image[0]) * len(self.image[1]) * len(self.image[2]) * self.duration)

            t = np.linspace(0, self.duration, int(self.sample_rate * self.duration), endpoint=False)
            self.audio = np.array([np.sin(2 * np.pi * f * t) for f in self.outputFreqs])

            binary_repr_v = np.vectorize(np.binary_repr)
            image_bitvector = "".join(binary_repr_v(self.image.flatten(), 8))
            #image_bitvector = "000000010000"
            
            n = 4

            counter = 0
            output_audio = np.zeros(0)
            debugstring = ""

            if self.sendbinary:
                for i in range(0, len(self.image.flatten()), 4):               
                    pixvector = 0
                    pixcount = 0
                    
                    for pixel in self.image.flatten()[i:i+4]:
                        if pixel == 0:
                            pixvector |= (1 << (3 - pixcount))
                        pixcount += 1

                    #print(f"{pixvector:04b}")

                    bytearr = np.zeros(t.size)
                    bytearr += self.audio[pixvector]
                    debugstring += f"{pixvector:04b}"

                    #if counter % 2 == 0:
                    #    bytearr += self.audio[-1]

                    counter += 1

                    if counter == 1:
                        output_audio = np.append(output_audio, [self.audio[-1], self.audio[-1], self.audio[-1], self.audio[-1]])
                    else:
                        output_audio = np.append(output_audio, self.audio[-1][len(self.audio[-1])//2:])
                    output_audio = np.append(output_audio, bytearr)

                    if (counter % 500 == 0):
                        print("Playing chunk!")
                        sd.play(output_audio, self.sample_rate)
                        sd.wait()
                        output_audio = np.zeros(0)
            else:
                #3 bytes makes one pixel (3 color channels)
                for i in range(0, len(image_bitvector), n):
                    #raw = image_bitvector[i:i+n]
                    #data = [int(b) for b in raw]
                    #self.encodedBits = data
                    #self.encodedBits = self.encodeHamming(data)
                    #temp = np.append(self.encodedBits, int(counter % 2 == 0))
                    #print(hex(int("".join(map(str, temp)), 2)), int(counter % 2 == 0))
                    #print(self.encodedBits, int(counter % 2 == 0))

                    idx = int(image_bitvector[i:i+n], 2)
                    #print(image_bitvector[i:i+n], idx, int(counter % 2 == 0))
                    bytearr = np.zeros(t.size)
                    bytearr += self.audio[idx]

                    """
                    if (self.multiFSK):
                        if (idx_arr == []):
                            for bit in range(0, 16, 4):
                                idx = int("".join(map(str, self.encodedBits[bit:bit+4])), 2)
                                #print(idx)
                                idx_arr.append(idx)

                        #print(idx_arr[0], int(counter % 2 == 0))
                        
                    else:
                        for i in range(0, 15):
                            if self.encodedBits[i] == 1:
                                bytearr += self.audio[i]
                    """

                    if counter % 2 == 0:
                        print("Binary: ", image_bitvector[i:i+(n*2)])
                        bytearr += self.audio[-1]

                    counter += 1

                    output_audio = np.append(output_audio, bytearr)

                    if (counter % 500 == 0):
                        print("Playing chunk!")
                        #scipy.io.wavfile.write("temp.wav", self.sample_rate, output_audio)
                        sd.play(output_audio, self.sample_rate)
                        sd.wait()
                        output_audio = np.zeros(0)

            spacer = 8
            print("\n".join(debugstring[i:i+spacer] for i in range(0, len(debugstring), spacer)))

            sd.play(output_audio, self.sample_rate)
            sd.wait()
            output_audio = np.zeros(0)
            
            print("Image sent!")
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
        
    def duration_changed(self, text):
        if text != "":
            self.duration = int(text) / 1000
        else:
            self.duration = 0.2

    def generateSignal(self, outdata, frames, time, status):
        t = (self.phase + np.arange(frames)) / self.sample_rate
        # Sum a sine wave for each active frequency, then normalise
        signal = sum(np.sin(2 * np.pi * f * t) for f in self.activeFreqs)
        signal /= np.max(np.abs(signal))   #normalize
        outdata[:, 0] = signal.astype(np.float32)
        self.phase += frames

    def closeEvent(self, event):
        self.stop_tone()
        event.accept()

    def start_tone(self, freq):
        self.stop_tone()
        
        phase = [0.0]  
        
        def callback(outdata, frames, time, status):
            t = (phase[0] + np.arange(frames)) / self.sample_rate
            outdata[:, 0] = np.sin(2 * np.pi * freq * t).astype(np.float32)
            phase[0] += frames  

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


