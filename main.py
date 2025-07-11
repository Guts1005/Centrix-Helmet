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
        self.setWindowTitle("Construction Site Helmet - Preview")
        self.showFullScreen()

        self.imageCaptured.connect(self.finish_capture)

        self.camera = Camera()
        self.preview_widget = self.camera.start_preview()

        self.audio_recorder = AudioRecorder()
        self.video_recorder = VideoRecorder(self.camera, self.audio_recorder)
        self.audio_recording = False
        self.video_recording = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self.preview_widget, stretch=1)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.type_dropdown = QComboBox()
        categories = ["General", "Electrical", "Plumbing", "HVAC", "Patrician", 
                      "Loose furniture", "Light fixtures", "Flooring", "Ceiling", "Painting"]
        self.type_dropdown.addItems(categories)
        bottom_layout.addWidget(self.type_dropdown)

        self.video_btn = QPushButton("Start Video")
        self.video_btn.setFixedSize(150, 40)
        self.video_btn.clicked.connect(self.toggle_video_recording)
        bottom_layout.addWidget(self.video_btn)

        self.record_audio_checkbox = QCheckBox("Record Audio with Video")
        self.record_audio_checkbox.setChecked(True)
        bottom_layout.addWidget(self.record_audio_checkbox)

        self.capture_btn = QPushButton("Capture Image")
        self.capture_btn.setFixedSize(150, 40)
        self.capture_btn.clicked.connect(self.handle_capture_image)
        bottom_layout.addWidget(self.capture_btn)

        self.audio_btn = QPushButton("Start Audio")
        self.audio_btn.setFixedSize(150, 40)
        self.audio_btn.clicked.connect(self.toggle_audio_recording)
        bottom_layout.addWidget(self.audio_btn)

        self.advanced_btn = QPushButton("Advanced Options")
        self.advanced_btn.setFixedSize(150, 40)
        self.advanced_btn.clicked.connect(self.open_advanced_options)
        bottom_layout.addWidget(self.advanced_btn)

        bottom_layout.addStretch()

        self.close_btn = QPushButton("Close Session")
        self.close_btn.setFixedSize(150, 40)
        self.close_btn.clicked.connect(self.close_session)
        bottom_layout.addWidget(self.close_btn)

        main_layout.addLayout(bottom_layout)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("background-color: #EFEFEF; padding: 5px;")
        main_layout.addWidget(self.status_label)

        self.gpio_handler = GPIOHandler(self)
        self.attempt_reupload_failed_files()

    def open_advanced_options(self):
        dialog = AdvancedOptionsDialog(self.camera, self)
        dialog.exec_()

    def attempt_reupload_failed_files(self):
        failed_dirs = {
            "image": FAILED_IMAGES_DIR,
            "audio": FAILED_AUDIOS_DIR,
            "video": FAILED_VIDEOS_DIR,
        }
        for file_type, failed_dir in failed_dirs.items():
            if not os.path.exists(failed_dir):
                continue
            for file_name in os.listdir(failed_dir):
                file_path = os.path.join(failed_dir, file_name)
                print(f"Attempting re-upload of {file_path}")
                if file_type == "image":
                    success, resp = upload_image(file_path, "", "")
                elif file_type == "audio":
                    success, resp = upload_audio(file_path, "", "")
                elif file_type == "video":
                    success, resp = upload_video(file_path, "", "")
                if success:
                    os.remove(file_path)
                    print(f"Successfully re-uploaded and deleted {file_path}")
                else:
                    print(f"Failed again to upload {file_path}: {resp}")

    def handle_capture_image(self):
        self.capture_btn.setEnabled(False)
        threading.Thread(target=self.capture_image_worker, daemon=True).start()

    def capture_image_worker(self):
        msg = ""
        try:
            speak("Capturing image")
            category = self.type_dropdown.currentText().lower()
            capture_time = datetime.datetime.now().strftime("%H:%M:%S")
            image_path = self.camera.capture_image(category)
            success, resp = upload_image(image_path, capture_time, capture_time)
            if success:
                os.remove(image_path)
                msg = f"Image captured & uploaded: {image_path}"
                speak("Image captured")
            else:
                msg = f"Image captured but upload failed: {resp}"
                speak("Image upload failed")
        except Exception as e:
            msg = f"Image capture error: {e}"
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
            speak("Audio Started")
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
            speak("Audio Stopped")

    def toggle_video_recording(self):
        record_audio_with_video = self.record_audio_checkbox.isChecked()
        self.attempt_reupload_failed_files()
        category = self.type_dropdown.currentText().lower()
        if not self.video_recording:
            self.video_recorder.start_recording(with_audio=record_audio_with_video)
            self.video_recording = True
            self.video_btn.setText("Stop Video")
            self.status_label.setText("Video recording started...")
            speak("Video Started")
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
            speak("Video Stopped")

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
