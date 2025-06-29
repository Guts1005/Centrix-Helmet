# -*- coding: windows-1252 -*-
#!/usr/bin/env python3

import os
import datetime
import time
from picamera2 import Picamera2
from picamera2.previews.qt import QGlPicamera2
from led_handler import led_status_blink  # ? Correct blink import

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        self.preview_widget = None
        self.preview_started = False
        self.image_counter = 1
        os.makedirs("Images", exist_ok=True)

    def apply_video_transform(self, hflip=False, vflip=False, rotation=0, width=1920, height=1080):
        """
        Apply transformation settings for video recording with 1080p resolution.
        """
        config = self.picam2.create_video_configuration(main={"size": (width, height)})
        config["transform"] = {"hflip": hflip, "vflip": vflip, "rotation": rotation}
        self.picam2.configure(config)

    def start_preview(self):
        """
        Start the camera preview using Qt OpenGL widget (1080p preview).
        """
        if self.preview_started:
            return self.preview_widget

        self.preview_widget = QGlPicamera2(self.picam2, keep_ar=True)

        # Use 1080p for preview (better performance for video)
        config = self.picam2.create_preview_configuration(main={"size": (1920, 1080)})
        self.picam2.configure(config)

        self.picam2.start()
        self.preview_started = True
        return self.preview_widget

    def stop_preview(self):
        if self.preview_started:
            self.picam2.stop()
            self.preview_started = False

    def capture_image(self, media_category="general"):
        """
        Capture an image using max resolution (3280x2464).
        """
        sanitized_category = media_category.replace(" ", "_").lower()
        now = datetime.datetime.now()
        date_str = now.strftime("%d%b%Y").lower()
        time_str = now.strftime("%H%M%S")
        filename = os.path.join("Images", f"img_{self.image_counter}_{date_str}_{time_str}_{sanitized_category}.jpg")

        try:
            # Configure camera for max still resolution
            still_config = self.picam2.create_still_configuration(main={"size": (3280, 2464)})
            self.picam2.configure(still_config)
            self.picam2.start()
            time.sleep(0.2)  # Allow time for camera to warm up
            self.picam2.capture_file(filename)

            led_status_blink()  # ? Blink LED after capture
        except Exception as e:
            raise Exception("Capture failed: " + str(e))

        self.image_counter += 1
        return filename

    def update_controls(self, controls):
        normalized_controls = {key: value / 100.0 for key, value in controls.items()}
        try:
            self.picam2.set_controls(normalized_controls)
        except Exception as e:
            print("Error updating camera controls:", e)
