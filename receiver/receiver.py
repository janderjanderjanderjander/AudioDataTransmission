import numpy as np
import pyqtgraph as pg
import sounddevice as sd
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QGridLayout
from PyQt6.QtCore import QTimer

class ReceiverWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.sampleRate = 44100
        self.chunkSize = 2048
        self.cutoffLine = 40
        self.inputFreqs = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000]

        #Hamming
        self.parityPositions = {1, 2, 4, 8} 
        self.dataPositions = [p for p in range(1, 16) if p not in self.parityPositions]

        #For goertzel
        self.freqGain = {
            1000: 2.0,
            2000: 1.4,
            3000: 3,
            4000: 1.0,
            5000: 1.0,
            7000: 1.0,
            8000: 1.5,
            9000: 1.0,
            10000: 1.0,
            11000: 2.0,
            12000: 1.0,
            13000: 1.0,
            14000: 1.5,
            15000: 1.0,
            16000: 1.0
        }

        self.stream = sd.InputStream(
            samplerate=self.sampleRate,
            channels=1, # Mono
            blocksize=self.chunkSize
        )

        layout = QVBoxLayout()
        label = QLabel("Receiver")
        layout.addWidget(label)

        plotsLayout = QHBoxLayout()

        self.plot1 = pg.PlotWidget()
        self.plot2 = pg.PlotWidget()
        self.plot3 = pg.PlotWidget()

        plotsLayout.addWidget(self.plot1)
        plotsLayout.addWidget(self.plot2)
        plotsLayout.addWidget(self.plot3)

        self.plot1.setYRange(-1, 1)
        self.plot2.setYRange(0, 200)
        self.plot3.setYRange(0, 3)

        layout.addLayout(plotsLayout)
        self.setLayout(layout)

        self.dataLine = self.plot1.plot(pen='y')
        self.dataLine2 = self.plot2.plot(pen='y')
        self.dataLine3 = self.plot3.plot(pen='y')

        self.messageLabel = QLabel("No bytes yet")
        layout.addWidget(self.messageLabel)

        # Gain controls
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

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)        

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

        hamming15 = [0 if x < 1 else 1 for x in gData] # Normalize to 0 and 1

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
            corrected = gData
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

