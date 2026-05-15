import numpy as np
import pyqtgraph as pg
import sounddevice as sd
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import QTimer

class ReceiverWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.sampleRate = 44100
        self.chunkSize = 2048
        self.cutoffLine = 40
        self.inputFreqs = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000]

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
        self.plot3.setYRange(0, 1)

        layout.addLayout(plotsLayout)
        self.setLayout(layout)

        self.dataLine = self.plot1.plot(pen='y')
        self.dataLine2 = self.plot2.plot(pen='y')
        self.dataLine3 = self.plot3.plot(pen='y')

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)        

    def startListening(self):
        self.stream.start()
        self.timer.start(30)


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
        print(gData)

        self.dataLine.setData(data)
        self.dataLine2.setData(fData)
        self.dataLine3.setData(gData)

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
        return magnitude


















        # cutoffLine = 3
        # start = 1000.0 #Madalaim sagedus
        # delta = 100.0 #Kahe sageduse vahe
        # n = 9          #Mitu sageduskomponenti me lisame (9-s on nö clock)
        # clock = 0
        # last_clock = 0
        # BUFFER_SIZE = 4
        # frame_buffer = []
        # bitStream = []

        # inputFreqs = start + delta * np.arange(n)
#     def bits_to_bytes(bit_stream):
#         '''
#         Turns a list of bits into a byte
#         '''
#         result = bytearray()

#         for bits in bit_stream:
#             # drop parity
#             data_bits = bits[:-1]
#             # reverse cause MSB and LSB are reversed  
#             data_bits = data_bits[::-1]
#             byte = int("".join(map(str, data_bits)), 2)
#             result.append(byte)

#         return result

#     def save_png(self):
#         global bitStream 

#         data = bits_to_bytes(bitStream)

#         with open("./common/pics/output.png", "wb") as f:
#             f.write(data)

#         print("Saved output.png")    

#     def getData():
#         #Get one chunk of data
#         samples, overflowed = stream.read(chunkSize)
#         if overflowed:
#             print("ERROR: Overflow")
#         samples = samples.flatten() # Convert 1xI into Ix1

#         # Windowing using hanning
#         windowed = samples * np.hanning(len(samples))

#         fft = np.fft.fft(windowed)
#         powers = abs(fft)[(inputFreqs / (sampleRate / chunkSize)).astype(np.int16)]

#         return powers

#     def startListening(self):




#         '''
#         if 
#             sampleRate = 48000 # Hz
#             chunkSize = 4800 # Δf = 10 Hz
#         then
#             1000 Hz → bin 100
#             2000 Hz → bin 200
#             3000 Hz → bin 300
#         '''

# #DEBUG quitting the program with q and saving with s
# # class MainWindow(QtWidgets.QWidget):
# #     def keyPressEvent(self, event):
# #         if event.key() == QtCore.Qt.Key.Key_Q:
# #             stream.stop()
# #             stream.close()

# #             QtWidgets.QApplication.quit()

# #         elif event.key() == QtCore.Qt.Key.Key_S:
# #             stream.stop()
# #             stream.close()

# #             QtWidgets.QApplication.quit()

# #             self.save_png()

            




    
# def update():
#     global clock, last_clock, bitStream
#     #Timer handler
#     data = getData()

#     p = [1 if x > cutoffLine else 0 for x in data]

#     clock = p[-1]

#     if clock !=  last_clock:
#         #print(data, p)

#         print(hex(int("".join(map(str, p[:-1][::-1])), 2)))

#         bitStream.append(p)
        
#         last_clock = clock



# def main():
#     app = QtWidgets.QApplication([])
#     window = MainWindow()
#     window.show()

#     #Microphone ON
#     stream.start()

#     #Timer for updates
#     timer = QtCore.QTimer()
#     timer.timeout.connect(update)
#     #inteval needs to be faster than chunkSize / sampleRate, which is how fast data comes in. Right now it's 46.4 ms
#     timer.start(10)

#     app.exec()

# if __name__ == "__main__":
#     main()
