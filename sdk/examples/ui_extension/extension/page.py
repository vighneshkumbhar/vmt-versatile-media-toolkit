from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import QTimer, QTime

class UIExamplePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("UI Example Extension v1.0.0"))
        layout.addWidget(QLabel("Hello from extension!"))
        
        self.time_label = QLabel()
        layout.addWidget(self.time_label)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
        
        btn = QPushButton("Click Me")
        btn.clicked.connect(self.show_msg)
        layout.addWidget(btn)
        
    def update_time(self):
        self.time_label.setText(QTime.currentTime().toString())
        
    def show_msg(self):
        QMessageBox.information(self, "Message", "Button clicked!")
