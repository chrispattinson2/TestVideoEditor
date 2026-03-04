import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTabWidget, QDoubleSpinBox,
    QLineEdit, QMessageBox, QProgressBar, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip


# Worker thread (keeps UI responsive during processing)
class WorkerThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, task, **kwargs):
        super().__init__()
        self.task = task
        self.kwargs = kwargs

    def run(self):
        try:
            if self.task == "merge":
                self._merge()
            elif self.task == "cut":
                self._cut()
            elif self.task == "audio":
                self._audio()
            self.finished.emit(True, "Done! File saved successfully.")
        except Exception as e:
            self.finished.emit(False, str(e))

    def _merge(self):
        self.progress.emit("Loading clips...")
        clips = [VideoFileClip(p) for p in self.kwargs["paths"]]
        self.progress.emit("Merging clips...")
        final = concatenate_videoclips(clips, method="compose")
        self.progress.emit("Exporting...")
        final.write_videofile(self.kwargs["output"], logger=None)
        for c in clips:
            c.close()
        final.close()

    def _cut(self):
        self.progress.emit("Loading clip...")
        clip = VideoFileClip(self.kwargs["path"])
        self.progress.emit("Trimming...")
        trimmed = clip.subclipped(self.kwargs["start"], self.kwargs["end"] or clip.duration)
        self.progress.emit("Exporting...")
        trimmed.write_videofile(self.kwargs["output"], logger=None)
        clip.close()
        trimmed.close()

    def _audio(self):
        self.progress.emit("Loading clip...")
        clip = VideoFileClip(self.kwargs["path"])
        if self.kwargs.get("mute"):
            self.progress.emit("Muting audio...")
            result = clip.without_audio()
        else:
            self.progress.emit("Replacing audio...")
            new_audio = AudioFileClip(self.kwargs["audio_path"])
            if new_audio.duration > clip.duration:
                new_audio = new_audio.subclipped(0, clip.duration)
            result = clip.with_audio(new_audio)
        self.progress.emit("Exporting...")
        result.write_videofile(self.kwargs["output"], logger=None)
        clip.close()
        result.close()


class FilePicker(QWidget):
    def __init__(self, label, filter_str="Video Files (*.mp4 *.mov *.avi *.mkv)"):
        super().__init__()
        self.filter_str = filter_str
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("No file selected...")
        self.path_edit.setReadOnly(True)
        btn = QPushButton(f"Browse {label}")
        btn.setFixedWidth(120)
        btn.clicked.connect(self._browse)
        layout.addWidget(self.path_edit)
        layout.addWidget(btn)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", self.filter_str)
        if path:
            self.path_edit.setText(path)

    def path(self):
        return self.path_edit.text()


class MergeTab(QWidget):
    def __init__(self, status_cb, progress_bar):
        super().__init__()
        self.status_cb = status_cb
        self.progress_bar = progress_bar
        self.pickers = []
        self.worker = None
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        grp = QGroupBox("Video Files to Merge (in order)")
        grp_layout = QVBoxLayout(grp)
        for i in range(1, 3):
            picker = FilePicker(f"Video {i}")
            self.pickers.append(picker)
            grp_layout.addWidget(QLabel(f"Video {i}:"))
            grp_layout.addWidget(picker)
        add_btn = QPushButton("+ Add another video")
        add_btn.clicked.connect(lambda: self._add_picker(grp_layout))
        grp_layout.addWidget(add_btn)
        layout.addWidget(grp)
        run_btn = QPushButton("Merge Videos")
        run_btn.setFixedHeight(36)
        run_btn.clicked.connect(self._run)
        layout.addWidget(run_btn)
        layout.addStretch()

    def _add_picker(self, layout):
        idx = len(self.pickers) + 1
        picker = FilePicker(f"Video {idx}")
        self.pickers.append(picker)
        layout.insertWidget(layout.count() - 1, QLabel(f"Video {idx}:"))
        layout.insertWidget(layout.count() - 1, picker)

    def _run(self):
        paths = [p.path() for p in self.pickers if p.path()]
        if len(paths) < 2:
            QMessageBox.warning(self, "Error", "Select at least 2 video files.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save Merged Video", "merged.mp4", "MP4 (*.mp4)")
        if not output:
            return
        self._start(WorkerThread("merge", paths=paths, output=output))

    def _start(self, worker):
        self.worker = worker
        self.worker.progress.connect(self.status_cb)
        self.worker.finished.connect(self._done)
        self.progress_bar.setRange(0, 0)
        self.worker.start()

    def _done(self, ok, msg):
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        (QMessageBox.information if ok else QMessageBox.critical)(self, "Result", msg)
        self.status_cb("Ready")


class CutTab(QWidget):
    def __init__(self, status_cb, progress_bar):
        super().__init__()
        self.status_cb = status_cb
        self.progress_bar = progress_bar
        self.worker = None
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        self.picker = FilePicker("Video")
        layout.addWidget(QLabel("Source Video:"))
        layout.addWidget(self.picker)
        time_grp = QGroupBox("Trim Range (seconds)")
        time_layout = QHBoxLayout(time_grp)
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0, 86400)
        self.start_spin.setDecimals(2)
        self.start_spin.setSuffix(" s")
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0, 86400)
        self.end_spin.setDecimals(2)
        self.end_spin.setSuffix(" s")
        self.end_spin.setSpecialValueText("End of video")
        time_layout.addWidget(QLabel("Start:"))
        time_layout.addWidget(self.start_spin)
        time_layout.addSpacing(20)
        time_layout.addWidget(QLabel("End:"))
        time_layout.addWidget(self.end_spin)
        layout.addWidget(time_grp)
        run_btn = QPushButton("Trim Video")
        run_btn.setFixedHeight(36)
        run_btn.clicked.connect(self._run)
        layout.addWidget(run_btn)
        layout.addStretch()

    def _run(self):
        src = self.picker.path()
        if not src:
            QMessageBox.warning(self, "Error", "Select a source video.")
            return
        start = self.start_spin.value()
        end = self.end_spin.value() or None
        if end and end <= start:
            QMessageBox.warning(self, "Error", "End time must be greater than start time.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save Trimmed Video", "trimmed.mp4", "MP4 (*.mp4)")
        if not output:
            return
        self.worker = WorkerThread("cut", path=src, start=start, end=end, output=output)
        self.worker.progress.connect(self.status_cb)
        self.worker.finished.connect(self._done)
        self.progress_bar.setRange(0, 0)
        self.worker.start()

    def _done(self, ok, msg):
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        (QMessageBox.information if ok else QMessageBox.critical)(self, "Result", msg)
        self.status_cb("Ready")


class AudioTab(QWidget):
    def __init__(self, status_cb, progress_bar):
        super().__init__()
        self.status_cb = status_cb
        self.progress_bar = progress_bar
        self.worker = None
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        self.video_picker = FilePicker("Video")
        layout.addWidget(QLabel("Source Video:"))
        layout.addWidget(self.video_picker)
        audio_grp = QGroupBox("Audio Action")
        audio_layout = QVBoxLayout(audio_grp)
        self.mute_chk = QCheckBox("Mute video (remove audio)")
        self.mute_chk.toggled.connect(self._toggle_mute)
        audio_layout.addWidget(self.mute_chk)
        self.audio_label = QLabel("Replace with audio file:")
        self.audio_picker = FilePicker("Audio", "Audio Files (*.mp3 *.wav *.aac *.ogg *.m4a)")
        audio_layout.addWidget(self.audio_label)
        audio_layout.addWidget(self.audio_picker)
        layout.addWidget(audio_grp)
        run_btn = QPushButton("Apply Audio Changes")
        run_btn.setFixedHeight(36)
        run_btn.clicked.connect(self._run)
        layout.addWidget(run_btn)
        layout.addStretch()

    def _toggle_mute(self, checked):
        self.audio_label.setEnabled(not checked)
        self.audio_picker.setEnabled(not checked)

    def _run(self):
        src = self.video_picker.path()
        if not src:
            QMessageBox.warning(self, "Error", "Select a source video.")
            return
        mute = self.mute_chk.isChecked()
        audio_path = self.audio_picker.path()
        if not mute and not audio_path:
            QMessageBox.warning(self, "Error", "Select an audio file or check Mute.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save Video", "output.mp4", "MP4 (*.mp4)")
        if not output:
            return
        self.worker = WorkerThread("audio", path=src, mute=mute, audio_path=audio_path, output=output)
        self.worker.progress.connect(self.status_cb)
        self.worker.finished.connect(self._done)
        self.progress_bar.setRange(0, 0)
        self.worker.start()

    def _done(self, ok, msg):
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        (QMessageBox.information if ok else QMessageBox.critical)(self, "Result", msg)
        self.status_cb("Ready")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MP4 Video Editor")
        self.setMinimumSize(600, 420)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        title = QLabel("MP4 Video Editor")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        root.addWidget(title)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-size: 12px;")
        tabs = QTabWidget()
        tabs.addTab(MergeTab(self._set_status, self.progress_bar), "Merge")
        tabs.addTab(CutTab(self._set_status, self.progress_bar), "Cut / Trim")
        tabs.addTab(AudioTab(self._set_status, self.progress_bar), "Audio")
        root.addWidget(tabs)
        root.addWidget(self.progress_bar)
        root.addWidget(self.status_label)
        self._apply_style()

    def _set_status(self, msg):
        self.status_label.setText(msg)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #1e1e2e; }
            QWidget { background: #1e1e2e; color: #cdd6f4; font-size: 13px; }
            QTabWidget::pane { border: 1px solid #45475a; border-radius: 4px; }
            QTabBar::tab { background: #313244; padding: 8px 18px; margin-right: 2px; border-radius: 4px 4px 0 0; }
            QTabBar::tab:selected { background: #89b4fa; color: #1e1e2e; font-weight: bold; }
            QPushButton { background: #89b4fa; color: #1e1e2e; border-radius: 5px; padding: 6px 14px; font-weight: bold; }
            QPushButton:hover { background: #b4befe; }
            QPushButton:pressed { background: #74c7ec; }
            QLineEdit { background: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; }
            QGroupBox { border: 1px solid #45475a; border-radius: 6px; margin-top: 8px; padding-top: 6px; }
            QGroupBox::title { color: #89b4fa; }
            QDoubleSpinBox { background: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 4px; }
            QProgressBar { border: 1px solid #45475a; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background: #89b4fa; border-radius: 4px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #89b4fa; border-radius: 3px; }
            QCheckBox::indicator:checked { background: #89b4fa; }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
