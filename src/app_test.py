import sys
from agents.planner_state import PlannerState
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject, QUrl
from PyQt5.QtGui import QPixmap
import os
from agents.graph import PlannerGraph
import time
import uuid
from threading import Event
from langgraph.types import Command
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from PyQt5.QtCore import pyqtSignal, QObject

engine_params = {
    "engine_type": "gemini",
    "model": "gemini-2.5-flash",
    "base_url": "https://generativelanguage.googleapis.com/v1beta",
    "api_key": "AIzaSyCf2UGdSxr1I4uNdHT2oCLni8SXw011mLA",
    "temperature": None,
}

class ImageEventHandler(FileSystemEventHandler, QObject):
    new_image_signal = pyqtSignal(str)

    def __init__(self):
        FileSystemEventHandler.__init__(self)
        QObject.__init__(self)

    def on_created(self, event):
        if event.src_path.endswith(".done"):
            png_path = event.src_path.replace(".done", ".png")
            self.new_image_signal.emit(png_path)

class EmittingStream(QObject):
    text_written = pyqtSignal(str)

    def write(self, text):
        if text.strip():
            self.text_written.emit(str(text))

    def flush(self):
        pass

class DualStream:
    def __init__(self, stream1, stream2):
        self.stream1 = stream1  # terminal
        self.stream2 = stream2  # PyQt emitting stream

    def write(self, text):
        if text.strip():
            self.stream1.write(text)
            self.stream1.flush()
            self.stream2.write(text)

    def flush(self):
        self.stream1.flush()

class GraphThread(QThread):
    log_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(dict)

    def __init__(self, graph, query):
        super().__init__()
        self.graph = graph
        self.query = query

    def run(self):
        graph = self.graph
        query = self.query

        initial = PlannerState(query=query)
        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
            }
        }
        result = graph.graph.invoke(initial, config)
        self.log_signal.emit(str(result))

        self.current_result = result

        while "__interrupt__" in result:
            reason = result['__interrupt__'][-1].value
            self.log_signal.emit(f"[INTERRUPT] {reason}")
        
            self.finish_signal.emit({"status": "WAIT_USER"})
        
            self.resume_event = Event()
            self.resume_event.wait()     

            self.log_signal.emit("Resuming...")
            time.sleep(3)

            result = graph.graph.invoke(Command(resume=True), config=config)
            self.log_signal.emit(str(result))
            self.current_result = result

        self.finish_signal.emit(result)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Computer Use App")

        layout = QVBoxLayout()

        font = self.font()
        font.setPointSize(13)
        self.setFont(font)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(QLabel("Graph Logs:"))
        layout.addWidget(self.log_box)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(QLabel("Latest Screenshot:"))
        layout.addWidget(self.image_label)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.start_graph)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.run_button)
        layout.addLayout(input_layout)

        self.setLayout(layout)

        self.stdout_stream = EmittingStream()
        self.stdout_stream.text_written.connect(self.add_log)
        self.original_stdout = sys.stdout
        sys.stdout = DualStream(self.original_stdout, self.stdout_stream)

        self.graph_thread = None

        self.setup_watcher()

    def handle_new_image(self, image_path):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.log_box.append("[Error] Cannot load image.")
            return

        scaled = pixmap.scaled(
            500, 300, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(scaled)

        #self.log_box.append(f'<img src="{image_path}" width="300">')
        # pixmap = QPixmap(image_path)
        # if pixmap.isNull():
        #     self.log_box.append("[Error] Could not load image.")
        #     return
        
        # # self.log_box.document().addResource(
        # #     2,  
        # #     QUrl(image_path),
        # #     pixmap
        # # )

        # # insert image HTML
        # self.log_box.insertHtml(f'<img src="{image_path}" width="1500" height="auto">')
        # self.log_box.ensureCursorVisible()
    

    def setup_watcher(self):
        folder = "D:\Learning\Project\CUA_App\src\screenshot"
        self.event_handler = ImageEventHandler()
        self.event_handler.new_image_signal.connect(self.handle_new_image)

        self.observer = Observer()
        self.observer.schedule(self.event_handler, folder, recursive=False)
        self.observer.start()

    def bring_to_front(self):
        self.hide()

        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.show()
        self.raise_()
        self.activateWindow()

        def remove_flag():
            self.hide()
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()

        QTimer.singleShot(300, remove_flag)

    def start_graph(self):
        query = self.input_field.text()
        if not query:
            return
        
        if query.lower() == "continue" and self.graph_thread:
            if self.graph_thread.resume_event:
                self.log_box.append("User requested continue...")
                self.graph_thread.resume_event.set()
            self.input_field.clear()
            return

        self.log_box.append(f"Running: {query}")

        new_graph = PlannerGraph(engine_params)
        self.graph_thread = GraphThread(new_graph, query)
        self.graph_thread.log_signal.connect(self.add_log)
        self.graph_thread.finish_signal.connect(self.handle_finish)
        self.graph_thread.start()
    
    def append_image(self, path):
        if not os.path.exists(path):
            self.log_box.append(f"Không tìm thấy file ảnh: {path}")
            return
        
        cursor = self.log_box.textCursor()
        cursor.insertHtml(f'<img src="{path}" width="400"><br>')
        self.log_box.ensureCursorVisible()

    def add_log(self, msg):
        self.log_box.append(msg)

        if msg.startswith("SCREENSHOT:"):
            path = msg.split("SCREENSHOT:")[1].strip()
            self.append_image(path)

    def handle_finish(self, result):
        if isinstance(result, dict) and result.get("status") == "WAIT_USER":
            self.log_box.append("!!! Graph paused — enter 'continue' to resume")
            self.bring_to_front()
            return

        self.log_box.append("--- GRAPH FINISHED ---")
        self.log_box.append(str(result))
        self.bring_to_front()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(700, 600)
    window.show()
    sys.exit(app.exec_())
