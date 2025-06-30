#!/usr/bin/env python3

import sys
import threading
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, QComboBox,
    QDialog, QSlider, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from camera import Camera
from recorder import AudioRecorder, VideoRecorder
from uploader import upload_image, upload_audio, upload_video
from gpio_handler import GPIOHandler
from utils import FAILED_IMAGES_DIR, FAILED_VIDEOS_DIR, FAILED_AUDIOS_DIR, speak  # <- speak added

class AdvancedOptionsDialog(QDialog):
    def __init__(self, camera, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Camera Settings")
        self.camera = camera
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.brightness_label = QLabel("Brightness:")
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(50)
        self.brightness_slider.valueChanged.connect(self.update_camera_controls)
        layout.addWidget(self.brightness_label)
        layout.addWidget(self.brightness_slider)

        self.sharpness_label = QLabel("Sharpness:")
        self.sharpness_slider = QSlider(Qt.Horizontal)
        self.sharpness_slider.setRange(0, 100)
        self.sharpness_slider.setValue(50)
        self.sharpness_slider.valueChanged.connect(self.update_camera_controls)
        layout.addWidget(self.sharpness_label)
        layout.addWidget(self.sharpness_slider)

        self.contrast_label = QLabel("Contrast:")
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(0, 100)
        self.contrast_slider.setValue(50)
        self.contrast_slider.valueChanged.connect(self.update_camera_controls)
        layout.addWidget(self.contrast_label)
        layout.addWidget(self.contrast_slider)

        self.saturation_label = QLabel("Saturation:")
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setRange(0, 100)
        self.saturation_slider.setValue(50)
        self.saturation_slider.valueChanged.connect(self.update_camera_controls)
        layout.addWidget(self.saturation_label)
        layout.addWidget(self.saturation_slider)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def update_camera_controls(self):
        brightness = self.brightness_slider.value()
        controls = {"Brightness": brightness}
        self.camera.update_controls(controls)


class MainWindow(QMainWindow):
    imageCaptured = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        ...
        self.imageCaptured.connect(self.finish_capture)
        ...

    def handle_capture_image(self):
        self.capture_btn.setEnabled(False)
        threading.Thread(target=self.capture_image_worker, daemon=True).start()

    def capture_image_worker(self):
        msg = ""
        try:
            speak("Capturing image")
            category = self.type_dropdown.currentText().lower()
            print("Selected category:", category)

            capture_time = datetime.datetime.now().strftime("%H:%M:%S")
            print("Capture time:", capture_time)

            image_path = self.camera.capture_image(category)
            print("Image saved at:", image_path)

            success, resp = upload_image(image_path, capture_time, capture_time)
            print("Upload response:", success, resp)

            if success:
                os.remove(image_path)
                msg = f"Image captured & uploaded: {image_path}"
                speak("Image captured")
            else:
                msg = f"Image captured but upload failed: {resp}"
                speak("Image upload failed")

        except Exception as e:
            msg = f"Image capture error: {e}"
            print("[ERROR] Image capture error:", e)
            speak("Image capture failed")

        finally:
            self.imageCaptured.emit(msg)

    @pyqtSlot(str)
    def finish_capture(self, msg):
        self.status_label.setText(msg)
        self.capture_btn.setEnabled(True)

    def toggle_audio_recording(self):
        if not self.audio_recording:
            self.audio_recorder.start_recording()
            self.audio_recording = True
            self.audio_btn.setText("Stop Audio")
            self.status_label.setText("Audio recording started...")
            speak("Audio Start")
        else:
            category = self.type_dropdown.currentText().lower()
            audio_file, start_time, end_time = self.audio_recorder.stop_recording(category)
            self.audio_recording = False
            self.audio_btn.setText("Start Audio")
            success, resp = upload_audio(audio_file, start_time, end_time)
            if success:
                os.remove(audio_file)
                self.status_label.setText(f"Audio recorded & uploaded: {audio_file}")
            else:
                self.status_label.setText(f"Audio recorded but upload failed: {resp}")
            speak("Audio Stop")

    def toggle_video_recording(self):
        record_audio_with_video = self.record_audio_checkbox.isChecked()
        self.attempt_reupload_failed_files()
        category = self.type_dropdown.currentText().lower()
        if not self.video_recording:
            self.video_recorder.start_recording(with_audio=record_audio_with_video)
            self.video_recording = True
            self.video_btn.setText("Stop Video")
            self.status_label.setText("Video recording started...")
            speak("Video Start")
        else:
            segments = self.video_recorder.stop_recording(category)
            self.video_recording = False
            self.video_btn.setText("Start Video")
            if segments:
                msg_list = []
                for seg in segments:
                    seg_file = seg["file"]
                    start_time = seg["start"]
                    end_time = seg["end"]
                    success, resp = upload_video(seg_file, start_time, end_time)
                    if success:
                        os.remove(seg_file)
                        msg_list.append(seg_file)
                    else:
                        msg_list.append(f"{seg_file} (upload failed)")
                self.status_label.setText("Video segments recorded: " + ", ".join(msg_list))
            else:
                self.status_label.setText("No video segments recorded.")
            speak("Video Stop")

    def close_session(self):
        self.camera.stop_preview()
        if self.audio_recording:
            self.audio_recorder.stop_recording(self.type_dropdown.currentText().lower())
        if self.video_recording:
            self.video_recorder.stop_recording(self.type_dropdown.currentText().lower())
        self.gpio_handler.cleanup()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
