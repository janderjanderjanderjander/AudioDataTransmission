import cv2
import json
import numpy as np
import pyqtgraph as pg
import sounddevice as sd
from lib.audio import getData
from PyQt6.QtCore import QTimer, Qt
from lib.hamming import decodeHamming
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QGridLayout

class ReceiverWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Debugging variables
        self.byteShowDebug = 0
        self.graphDebug = 0
        self.gainDebug = 0
        self.picGen = 1
        self.calibration = 0

        #Calibration
        self.count = 0
        self.targetAmp = 10
        self.maxRatio = 0

        #new
        self.byteBuffer = []
        self.state = 0
        self.sizeX = 20
        self.sizeY = 20
        self.prevOnesAndZeros = []

        #Filtering
        self.sampleRate = 44100
        self.chunkSize = 300
        #self.cutoffLine = 
        self.prevOnesAndZeros = None
        self.sameCount = 0
        self.inputFreqs = np.round(np.linspace(1000, 15000, 17)) 

        self.parityPositions = {1, 2, 4, 8} 
        self.dataPositions = [p for p in range(1, 16) if p not in self.parityPositions]
        # if ratio > self.maxRatio:
        #     self.maxRatio = ratio
        self.freqGain = {freq: 1.0 for freq in self.inputFreqs}

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
            self.plot3.setYRange(0, 25)

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

            # Pic init
            self.frame = np.zeros((self.sizeY, self.sizeX), dtype=np.uint8)   

            self.refreshCanvas()
            self.x = 0
            self.y = 0

            # Receiving pic
            self.picBuffer = []
            self.prevSyncBit = 0
            self.gotValue = True

            # Show byte
            self.setLayout(layout)
            self.messageLabel = QLabel("No bytes yet")
            layout.addWidget(self.messageLabel)

            # Receive pic
            self.timer = QTimer()
            self.timer.timeout.connect(self.updatePicBuffer)        
            self.stream.start()
            self.timer.start(10)

            # If buffer has the 3 channels worth of info. so 24 bits, then update pixel using def setPixel(self, bits24: list[int]):
            # if len(self.picBuffer) >= 24:
            #     self.setPixel(self.picBuffer[:24])
            #     self.picBuffer = self.picBuffer[24:]


        self.setLayout(layout)

    def updatePicBuffer(self):
        
        gData = getData(self.stream, self.chunkSize, self.sampleRate, self.freqGain, self.inputFreqs, option=2)
        #print(f'Gdata : {gData}')
        max_val = max(gData)
        #print(f' Maximum: {max_val}')
        max_index = int(np.argmax(gData))
        others = [x for i, x in enumerate(gData) if i != max_index]
        avg_noise = sum(others) / len(others)

        ratio = max_val / avg_noise
        # if ratio > self.maxRatio:
        #     self.maxRatio = ratio
        #print(f'Max Ratio - {self.maxRatio}')
        onesAndZeros = [1 if x == max_val else 0 for x in gData]
        #print(''.join(str(b) for b in onesAndZeros)) #DEBUG GOOD PRINT
        #print(self.gotValue)
        #print(f'Ratio - {ratio}')

        if ratio < 25:
            return

        # if onesAndZeros != self.prevOnesAndZeros:
        #     self.prevOnesAndZeros = onesAndZeros
        #     self.sameCount = 1
        #     return

        # self.sameCount += 1

        # if self.sameCount < 3:
        #     return

        #print(''.join(str(b) for b in onesAndZeros)) #DEBUG GOOD PRINT

        syncBit = onesAndZeros[-1]

        if syncBit == 1: # Incoming transmittion
            self.state = 1

        if syncBit == 0 and self.state == 1: # Sync is over, time to catch
            self.state = 2
            if not(self.gotValue): # If this is None, means I didn't save any info. Insert 0000 to fix shift
                self.byteBuffer.append(f"0000")
                print(f'Nothing : {self.byteBuffer[-1]}')
            self.gotValue = False
        
        if self.state == 2: # Process

            for indeks, el in enumerate(onesAndZeros): # Every bit
                if el == 1:
                    if indeks != len(onesAndZeros) - 1:
                        self.gotValue = True
                        self.byteBuffer.append(f"{indeks:04b}")
                        #print(self.byteBuffer[-1])
                        self.state = 0
                

            if len(self.byteBuffer) >= 4:
                binValue = self.byteBuffer[0] + self.byteBuffer[1] + self.byteBuffer[2] + self.byteBuffer[3]
                #print(f' H: {binValue}')
                binList = [int(b) for b in binValue] #16 bits
                #binList = binList[:15] #15 bits
                
                #decoded = decodeHamming(binList, self.parityPositions) #fixed result
                decoded = binList
                #dataBits = [decoded[i-1] for i in range(1, 16) if i not in self.parityPositions] #11 bit
                dataBits = decoded
                # print(f' D: {dataBits}')
                # print("")

                #print(binValue)
                #print(dataBits)
                #x = input()

                for bit in dataBits:
                    self.setPixel(bit)

                    # Move to next pixel
                    self.x += 1

                    if self.x >= self.sizeX:
                        self.x = 0
                        self.y += 1

                    # Stop if 9x9 image is full
                    if self.y >= self.sizeY:
                        self.y = 8
                        self.x = 8
                        print("DONE")
                        self.timer.stop()
                        break

                self.byteBuffer = []

    def setPixel(self, bit: int):
        '''
        Sets one 1-bit pixel and updates canvas.
        bit should be:
        0 = black
        1 = white
        '''
        self.frame[self.y, self.x] = 1 if bit else 0
        self.refreshCanvas()

    def refreshCanvas(self):
        '''
        Converts the 9x9 1-bit-style numpy array to QPixmap.
        Internally frame stores 0 or 1.
        For display, it is converted to 0 or 255.
        '''
        display = (self.frame * 255).astype(np.uint8)

        h, w = display.shape
        qimg = QImage(
            display.data,
            w,
            h,
            w,
            QImage.Format.Format_Grayscale8
        )

        self.canvasPixmap = QPixmap.fromImage(qimg)

        # Optional: scale up so the 9x9 image is visible
        self.canvas.setPixmap(
            self.canvasPixmap.scaled(
                500,
                500,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
        )

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
            powers = getData(self.stream, self.chunkSize, self.sampleRate, self.freqGain, self.inputFreqs, option=2)
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

    def update(self):
        data = getData(self.stream, self.chunkSize, self.sampleRate, self.freqGain, self.inputFreqs)
        fData = getData(self.stream, self.chunkSize, self.sampleRate, self.freqGain, self.inputFreqs, option=1)
        gData = getData(self.stream, self.chunkSize, self.sampleRate, self.freqGain, self.inputFreqs, option=2)

        if self.graphDebug == 1:
            self.dataLine.setData(data)
            self.dataLine2.setData(fData)
            self.dataLine3.setData(gData)




