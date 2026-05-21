import sys
from receiver.receiver import ReceiverWidget
from sender.sender import SenderWidget


from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout
)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.resize(800, 500)
        self.layout = QVBoxLayout()

        self.receiverButton = QPushButton("Receiver")
        self.receiverButton.clicked.connect(self.showReceiver)
        self.senderButton = QPushButton("Sender")
        self.senderButton.clicked.connect(self.showSender)

        self.layout.addWidget(self.receiverButton)
        self.layout.addWidget(self.senderButton)

        self.setLayout(self.layout)

    def clearLayout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def showReceiver(self):
        self.clearLayout()

        receiver = ReceiverWidget()

        self.layout.addWidget(receiver)

    def showSender(self):
        self.clearLayout()

        sender = SenderWidget()
        
        self.layout.addWidget(sender)


app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())