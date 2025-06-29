import RPi.GPIO as GPIO
import time

# Define GPIOs
LED_STATUS = 5     # Camera Status LED
LED_AUDIO = 19     # Audio Recording LED
LED_RECORD = 26    # Video Recording LED

def setup_leds():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_STATUS, GPIO.OUT)
    GPIO.setup(LED_AUDIO, GPIO.OUT)
    GPIO.setup(LED_RECORD, GPIO.OUT)

    # Set initial states
    GPIO.output(LED_STATUS, GPIO.HIGH)   # Status ON at start
    GPIO.output(LED_AUDIO, GPIO.LOW)     # Audio OFF
    GPIO.output(LED_RECORD, GPIO.LOW)    # Record OFF

def led_status_on():
    GPIO.output(LED_STATUS, GPIO.HIGH)

def led_status_off():
    GPIO.output(LED_STATUS, GPIO.LOW)

def led_record_on():
    GPIO.output(LED_RECORD, GPIO.HIGH)

def led_record_off():
    GPIO.output(LED_RECORD, GPIO.LOW)

def led_audio_on():
    GPIO.output(LED_AUDIO, GPIO.HIGH)

def led_audio_off():
    GPIO.output(LED_AUDIO, GPIO.LOW)

def led_status_blink(duration=0.2):
    current_state = GPIO.input(LED_STATUS)
    GPIO.output(LED_STATUS, not current_state)
    time.sleep(duration)
    GPIO.output(LED_STATUS, current_state)

def cleanup_leds():
    GPIO.cleanup([LED_STATUS, LED_AUDIO, LED_RECORD])
