import numpy as np
import pyqtgraph as pg
import sounddevice as sd
from pyqtgraph.Qt import QtWidgets, QtCore

sampleRate = 44100 # Hz
chunkSize = 2048 

# Conigure input.
stream = sd.InputStream(
    samplerate=sampleRate,
    channels=1, # Mono
    blocksize=chunkSize
)

def getData():
    #Get one chunk of data
    samples, overflowed = stream.read(chunkSize)
    if overflowed:
        print("ERROR: Overflow")
    return samples.flatten() # Convert 1xI into Ix1 

    #TODO: Window function here

    #TODO: DFT

def update():
    #Timer handler
    data = getData()
    data_line.setData(data)

def main():

    stream.start()

    #DEBUG
    #Plot raw data
    global data_line
    app = QtWidgets.QApplication([])
    win = pg.GraphicsLayoutWidget(show=True, title="Raw Audio Input")
    plot = win.addPlot()
    data_line = plot.plot(pen='y')

    #Timer for updates
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    #inteval needs to be faster than chunkSize / sampleRate, which is how fast data comes in. Right now it's 46.4 ms
    timer.start(30)

    app.exec()

if __name__ == "__main__":
    main()
