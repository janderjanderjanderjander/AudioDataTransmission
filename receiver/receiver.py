import json
import cv2
import numpy as np
import pyqtgraph as pg
import sounddevice as sd
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QGridLayout
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt

class ReceiverWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Debugging variables
        self.byteShowDebug = 0
        self.graphDebug = 0
        self.gainDebug = 0
        self.picGen = 1
        #Calibration
        self.calibration = 0
        self.targetAmp = 10

        #Filtering
        self.sampleRate = 44100
        self.chunkSize = 2048
        self.cutoffLine = 0.5
        self.inputFreqs = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000]

        #Hamming
        self.parityPositions = {1, 2, 4, 8} 
        self.dataPositions = [p for p in range(1, 16) if p not in self.parityPositions]

        #Goertzel
        if self.calibration == 1:
            self.freqGain = {
                1000: 1.0,
                2000: 1.0,
                3000: 1.0,
                4000: 1.0,
                5000: 1.0,
                6000: 1.0,
                7000: 1.0,
                8000: 1.0,
                9000: 1.0,
                10000: 1.0,
                11000: 1.0,
                12000: 1.0,
                13000: 1.0,
                14000: 1.0,
                15000: 1.0
            }
        else:
            with open("common/config/calibrationGains.json", "r") as f:
                gains_serializable = json.load(f)
                self.freqGain = {int(k): v for k, v in gains_serializable.items()}

        #print(self.freqGain)

        self.stream = sd.InputStream(
            samplerate=self.sampleRate,
            channels=1, # Mono
            blocksize=self.chunkSize
        )

        layout = QVBoxLayout()
        label = QLabel("Receiver")
        layout.addWidget(label)

        # Graphing controls
        if self.graphDebug == 1:
            plotsLayout = QHBoxLayout()

            self.plot1 = pg.PlotWidget()
            self.plot2 = pg.PlotWidget()
            self.plot3 = pg.PlotWidget()

            plotsLayout.addWidget(self.plot1)
            plotsLayout.addWidget(self.plot2)
            plotsLayout.addWidget(self.plot3)

            self.plot1.setYRange(-1, 1)
            self.plot2.setYRange(0, 200)
            self.plot3.setYRange(0, 11)

            layout.addLayout(plotsLayout)

            self.dataLine = self.plot1.plot(pen='y')
            self.dataLine2 = self.plot2.plot(pen='y')
            self.dataLine3 = self.plot3.plot(pen='y')

        # Gain controls
        if self.gainDebug == 1:
            gainContainer = QWidget()
            gainLayout = QGridLayout()

            self.gainInputs = {}

            for row, freq in enumerate(self.inputFreqs):
                freqLabel = QLabel(f"{freq} Hz")

                gainInput = QLineEdit(str(self.freqGain.get(freq, 1.0)))
                gainInput.setFixedWidth(60)

                updateBtn = QPushButton("Update")

                # store reference
                self.gainInputs[freq] = gainInput

                # connect button
                updateBtn.clicked.connect(
                    lambda checked=False, f=freq: self.updateGain(f)
                )

                gainLayout.addWidget(freqLabel, row, 0)
                gainLayout.addWidget(gainInput, row, 1)
                gainLayout.addWidget(updateBtn, row, 2)

            gainContainer.setLayout(gainLayout)
            layout.addWidget(gainContainer)

        # Controls for showing received byte
        if self.byteShowDebug == 1:
            self.setLayout(layout)
            self.messageLabel = QLabel("No bytes yet")
            layout.addWidget(self.messageLabel)
            self.timer = QTimer()
            self.timer.timeout.connect(self.update)        
            self.timer.start()
            self.stream.start()

        # Calibration of goertzel gains
        if self.calibration == 1:
            # Amplitude calibration
            self.freqIndex = 0
            self.calibMeasurements = []
            self.stream.start()

            self.calibBTN = QPushButton("Next note")
            self.calibBTN.clicked.connect(self.calibrate)
            layout.addWidget(self.calibBTN)

        if self.picGen == 1:

            self.canvas = QLabel()
            self.canvas.setFixedSize(500, 500)
            self.canvas.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(self.canvas)

            # Init empty pic
            self.frame = np.zeros((500, 500, 3), dtype=np.uint8) 
            self.refreshCanvas()
            self.x = 0
            self.y = 0


            #DEBUGGING PART; LOSE THIS
            filePath = "common/pics/samplePicBlackNWhiteSmall.png"
            self.debugImg = cv2.imread(filePath)  # loads as BGR
            if self.debugImg is None:
                print(f"ERROR: Could not load image: {filePath}")
            self.debugPixelIndex = 0  # flat index into the image

            self.debugTimer = QTimer()
            self.debugTimer.timeout.connect(self.debugTick)
            self.debugTimer.start(30)  # 1 second interval 30 FOR NOW, too slow otherwise


        self.setLayout(layout)

    
    def setPixel(self, bits24: list[int]):
        '''
        Sets a pixel and updates canvas. Argument is a tuple of (b, g, r), because of opencv
        Call if u have 24 bit received.
        '''
        self.frame[self.y, self.x] = bits24
        self.refreshCanvas()

    def refreshCanvas(self):
        '''
        This converts the numpy array to QPixmap so we can have real time show
        '''
        rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.canvasPixmap = QPixmap.fromImage(qimg)
        self.canvas.setPixmap(self.canvasPixmap)



    def debugTick(self):
        """Reads 24 pixels from the debug image and feeds them in."""
        imgH, imgW = self.debugImg.shape[:2]
        totalPixels = imgH * imgW

        for i in range(1000): #1000 to see it. Too slow otherwise
            if self.debugPixelIndex >= totalPixels:
                self.debugTimer.stop()
                return

            # Convert flat index to x, y
            self.x = self.debugPixelIndex % imgW
            self.y = self.debugPixelIndex // imgW

            bgr = self.debugImg[self.y, self.x].tolist()
            self.setPixel(bgr)

            self.debugPixelIndex += 1


    def calibrate(self): 
        #Measure the amplitude of frequency
        count = 3
        samples = []
        while (count):
            powers = self.getData(option=2)
            samples.append(powers[self.freqIndex])
            count -= 1
        self.calibMeasurements.append(sum(samples) / 3)
        print(self.calibMeasurements[-1])
        self.freqIndex += 1
        if self.freqIndex >= len(self.inputFreqs):
            self.finishCalibration()

    def finishCalibration(self):
        for i, freq in enumerate(self.inputFreqs):
            avg = self.calibMeasurements[i]
            self.freqGain[freq] = self.targetAmp / avg

        gains_serializable = {str(k): v for k, v in self.freqGain.items()}
        
        with open("common/config/calibrationGains.json", "w") as f:
            json.dump(gains_serializable, f, indent=4)

        print(gains_serializable)
        print("Calibration complete, gains saved.")
        self.freqIndex = 0

    def updateGain(self, freq):
        try:
            value = float(self.gainInputs[freq].text())
            self.freqGain[freq] = value
            print(f"Updated {freq} Hz gain -> {value}")
        except ValueError:
            print(f"Invalid gain value for {freq} Hz")

    def setMessage(self, text):
        self.messageLabel.setText(text)

    def startListening(self):
        self.stream.start()
        self.timer.start(30)

    def updateByte(self, gData):
        '''
        Takes data as input
        Applies single error fix 
        If data passes filter, set message to it.
        Using hamming(15,11) noise filtering. Includes 4 parity bits which can fix 1 bit errors
        '''

        hamming15 = [0 if x < self.cutoffLine else 1 for x in gData] # Normalize to 0 and 1

        # See if any errors
        syndrome = 0
        for p in sorted(self.parityPositions): # {1, 2, 4, 8} 
            covered = []
            for pos in range(1, 16):      # pos = 1, 2, 3, ... 15
                if pos & p:                # anding check if the number is covered by the parity bit. 0 0 0 0 each digit has a master
                    covered.append(hamming15[pos - 1])  # grab the bit value at that position
            result = 0
            for bit in covered: # or everything to see if any problems.
                result = result ^ bit
            if result != 0: #if problems, add to syndrome
                syndrome += p

        # Unfixable
        if syndrome > 15:
            print("SYNDROME OB")

        # Single error fix
        elif syndrome != 0:
            corrected = hamming15
            corrected[syndrome - 1] ^= 1
            self.setMessage(str(corrected))

        # All good
        else:
            self.setMessage(str(hamming15))


    def getData(self, option=0):
        samples, overflowed = self.stream.read(self.chunkSize)

        if overflowed:
            print("ERROR: Overflow")

        samples = samples.flatten()

        if option == 1:
            windowed = samples * np.hanning(len(samples))
            freqDom = np.fft.rfft(windowed)
            magnitudes = np.abs(freqDom) #magnitudes
            return magnitudes

        if option == 2:
            windowed = samples * np.hanning(len(samples))
            powers = [self.goertzel(windowed, f, self.sampleRate) for f in self.inputFreqs]
            return powers

        return samples.flatten()

    def update(self):
        data = self.getData()
        fData = self.getData(option=1)
        gData = self.getData(option=2)

        if self.graphDebug == 1:
            self.dataLine.setData(data)
            self.dataLine2.setData(fData)
            self.dataLine3.setData(gData)

        self.updateByte(gData)


    # https://every-algorithm.github.io/2025/06/25/goertzel_algorithm.html
    def goertzel(self, samples, target_freq, sample_rate):
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

        adjustedMagnitude = magnitude * self.freqGain.get(target_freq, 1.0)

        return adjustedMagnitude

