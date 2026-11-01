from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel

class FFmpegExamplePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        self.lbl = QLabel("Select a media file")
        layout.addWidget(self.lbl)
        
        btn = QPushButton("Select File & Add Job")
        btn.clicked.connect(self.add_job)
        layout.addWidget(btn)
        
    def add_job(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Media")
        if file:
            self.lbl.setText(f"Selected: {file}")
            # ctx.ffmpeg.execute(["-i", file]) would be called here
