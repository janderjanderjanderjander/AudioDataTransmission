import numpy as np
import pyqtgraph as pg
import sounddevice as sd
from pyqtgraph.Qt import QtWidgets, QtCore

sampleRate = 48000 # Hz
chunkSize = 4800 # Δf = 10 Hz
cutoffLine = 1

inputFreqs = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000]

#Byte handling variables
last1 = last2 = last3 = last4 = lastP = []
lastParity = 0
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
            #print(bitStream)
            QtWidgets.QApplication.quit()

        elif event.key() == QtCore.Qt.Key.Key_S:
            stream.stop()
            stream.close()

            self.save_png()

            QtWidgets.QApplication.quit()

    def save_png(self):
        global bitStream 

        data = bits_to_bytes(bitStream)

        with open("./assets/output.png", "wb") as f:
            f.write(data)

        print("Saved output.png")

# https://every-algorithm.github.io/2025/06/25/goertzel_algorithm.html
def goertzel(samples, target_freq, sample_rate):
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

def getData():
    #Get one chunk of data
    samples, overflowed = stream.read(chunkSize)
    if overflowed:
        print("ERROR: Overflow")
    samples = samples.flatten() # Convert 1xI into Ix1

    # Windowing using hanning
    windowed = samples * np.hanning(len(samples))

    powers = [goertzel(windowed, f, sampleRate) for f in inputFreqs]
    return powers
    
def update():
    global last1, last2, last3, last4, lastP, lastParity, bitStream
    #Timer handler
    data = getData()

    
    #TODO: REMOVE, since this is just for readablity
    #Turn into nice numbers
    p = [int(round(float(x), 0) != 0) for x in data]

    #Check if byte is valid by checking 
    last4 = last3
    last3 = last2
    last2 = last1
    last1 = p
    parity = p[-1]

    values = [last1, last2, last3, last4]

    match = next((v for v in values if values.count(v) >= 3), None)

    if match is not None and lastP != p and lastParity != parity :
        lastP = p
        lastParity = parity


        #DEBUG
        #print(p)

        bitStream.append(p)


    #DEBUG
    #print(p)



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
    timer.start(30)

    app.exec()

if __name__ == "__main__":
    main()
