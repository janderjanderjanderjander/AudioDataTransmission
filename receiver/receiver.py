import numpy as np
import pyqtgraph as pg
import sounddevice as sd
from pyqtgraph.Qt import QtWidgets, QtCore

sampleRate = 48000 # Hz
chunkSize = 480 # Δf = 10 Hz
cutoffLine = 3

start = 1000.0 #Madalaim sagedus
delta = 100.0 #Kahe sageduse vahe
n = 9          #Mitu sageduskomponenti me lisame (9-s on nö clock)

inputFreqs = start + delta * np.arange(n)

clock = 0
last_clock = 0

frame_buffer = []
BUFFER_SIZE = 4

bitStream = []


'''
if 
    sampleRate = 48000 # Hz
    chunkSize = 4800 # Δf = 10 Hz
then
    1000 Hz → bin 100
    2000 Hz → bin 200
    3000 Hz → bin 300
'''

# Conigure input.
stream = sd.InputStream(
    samplerate=sampleRate,
    channels=1, # Mono
    blocksize=chunkSize
)

def bits_to_bytes(bit_stream):
    '''
    Turns a list of bits into a byte
    '''
    result = bytearray()

    for bits in bit_stream:
        # drop parity
        data_bits = bits[:-1]
        # reverse cause MSB and LSB are reversed  
        data_bits = data_bits[::-1]
        byte = int("".join(map(str, data_bits)), 2)
        result.append(byte)

    return result    

#DEBUG quitting the program with q and saving with s
class MainWindow(QtWidgets.QWidget):
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Q:
            stream.stop()
            stream.close()

            QtWidgets.QApplication.quit()

        elif event.key() == QtCore.Qt.Key.Key_S:
            stream.stop()
            stream.close()

            QtWidgets.QApplication.quit()

            self.save_png()

            

    def save_png(self):
        global bitStream 

        data = bits_to_bytes(bitStream)

        with open("./common/pics/output.png", "wb") as f:
            f.write(data)

        print("Saved output.png")

def getData():
    #Get one chunk of data
    samples, overflowed = stream.read(chunkSize)
    if overflowed:
        print("ERROR: Overflow")
    samples = samples.flatten() # Convert 1xI into Ix1

    # Windowing using hanning
    windowed = samples * np.hanning(len(samples))

    fft = np.fft.fft(windowed)
    powers = abs(fft)[(inputFreqs / (sampleRate / chunkSize)).astype(np.int16)]

    return powers
    
def update():
    global clock, last_clock, bitStream
    #Timer handler
    data = getData()

    p = [1 if x > cutoffLine else 0 for x in data]

    clock = p[-1]

    if clock !=  last_clock:
        #print(data, p)

        print(hex(int("".join(map(str, p[:-1][::-1])), 2)))

        bitStream.append(p)
        
        last_clock = clock



def main():
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()

    #Microphone ON
    stream.start()

    #Timer for updates
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    #inteval needs to be faster than chunkSize / sampleRate, which is how fast data comes in. Right now it's 46.4 ms
    timer.start(10)

    app.exec()

if __name__ == "__main__":
    main()
