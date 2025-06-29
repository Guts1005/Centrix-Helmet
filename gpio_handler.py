#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import threading
import os
from led_handler import setup_leds

class GPIOHandler:
    def __init__(self, main_window):
        self.main_window = main_window
        setup_leds()

        # GPIO mapping for both RF remote and backup physical buttons
        self.pin_to_action = {
            # RF Remote (YK04)
            22: self.main_window.toggle_audio_recording,     # RF Button A
            17: self.main_window.toggle_video_recording,     # RF Button B
            23: self.main_window.handle_capture_image,       # RF Button C
            27: self.shutdown_pi,                            # RF Button D

            # Backup Physical Buttons (new GPIOs)
            6:  self.main_window.toggle_audio_recording,     # Backup Button 1 (Pin 31)
            13: self.main_window.toggle_video_recording,     # Backup Button 2 (Pin 33)
            12: self.main_window.handle_capture_image        # Backup Button 3 (Pin 32)
        }

        self.rf_pins = [22, 17, 23, 27]
        self.backup_pins = [6, 13, 12]

        GPIO.setmode(GPIO.BCM)

        # Set correct pull-up/down for each type
        for pin in self.rf_pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        for pin in self.backup_pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.running = True
        self.poll_thread = threading.Thread(target=self.poll_gpio, daemon=True)
        self.poll_thread.start()

    def poll_gpio(self):
        last_state = {pin: GPIO.input(pin) for pin in self.pin_to_action}
        while self.running:
            for pin, action in self.pin_to_action.items():
                current_state = GPIO.input(pin)
                print(f"[GPIO DEBUG] Pin {pin}: {'HIGH' if current_state else 'LOW'}")

                # Detect press based on pin type
                if (
                    (pin in self.rf_pins and current_state == GPIO.HIGH and last_state[pin] == GPIO.LOW) or
                    (pin in self.backup_pins and current_state == GPIO.LOW and last_state[pin] == GPIO.HIGH)
                ):
                    try:
                        print(f"[GPIO] Button press detected on pin {pin}")
                        action()
                    except Exception as e:
                        print(f"[GPIO] Error on pin {pin}: {e}")
                    time.sleep(0.3)  # Debounce

                last_state[pin] = current_state
            time.sleep(0.05)

    def shutdown_pi(self):
        print("[GPIO] Shutdown initiated via RF remote.")
        os.system("sudo shutdown now")

    def cleanup(self):
        self.running = False
        self.poll_thread.join()
        GPIO.cleanup()
