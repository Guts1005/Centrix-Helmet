#!/usr/bin/env python3
import pyaudio
import wave
import threading
import datetime
import os
import time
import subprocess

# 🔁 Import LED control for recording indication
from led_handler import led_record_on, led_record_off, led_audio_on, led_audio_off

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class AudioRecorder:
    def __init__(self):
        os.makedirs("Audios", exist_ok=True)
        self.audio_thread = None
        self.stop_event = None
        self.temp_audio_file = os.path.join("Audios", "temp_audio.wav")
        self.recording_start_time = None
        self.audio_counter = 1
        self.segment_audio_thread = None
        self.segment_stop_event = None
        self.segment_temp_file = None
        self.segment_start_time = None

    def start_recording(self):
        if self.audio_thread and self.audio_thread.is_alive():
            return
        self.stop_event = threading.Event()
        self.recording_start_time = datetime.datetime.now()
        self.audio_thread = threading.Thread(target=self.record_audio, daemon=True)
        self.audio_thread.start()
        led_audio_on()  # Turn on audio LED

    def record_audio(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)
        frames = []
        while not self.stop_event.is_set():
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                print("Audio error:", e)
                continue
            frames.append(data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf = wave.open(self.temp_audio_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def stop_recording(self, media_category):
        if self.stop_event:
            self.stop_event.set()
        if self.audio_thread:
            self.audio_thread.join()

        led_audio_off()  # Turn off audio LED

        start = self.recording_start_time.strftime("%d%b%Y_%H%M%S").lower()
        end_time = datetime.datetime.now()
        end = end_time.strftime("%d%b%Y_%H%M%S").lower()
        start_hms = self.recording_start_time.strftime("%H:%M:%S")
        end_hms = end_time.strftime("%H:%M:%S")

        final_filename = os.path.join("Audios", f"audio_{self.audio_counter}_{start}_to_{end}_{media_category}.wav")

        try:
            os.rename(self.temp_audio_file, final_filename)
        except Exception as e:
            print("Error renaming audio file:", e)
            final_filename = self.temp_audio_file

        self.audio_counter += 1
        return final_filename, start_hms, end_hms

    def start_segmented_recording(self):
        self.segment_stop_event = threading.Event()
        self.segment_start_time = datetime.datetime.now()
        self.segment_temp_file = os.path.join("Audios", "temp_seg_audio.wav")
        self.segment_audio_thread = threading.Thread(target=self.record_segment_audio, daemon=True)
        self.segment_audio_thread.start()

    def record_segment_audio(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)
        frames = []
        while not self.segment_stop_event.is_set():
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                print("Segmented audio error:", e)
                continue
            frames.append(data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf = wave.open(self.segment_temp_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def stop_segmented_recording(self):
        if self.segment_stop_event:
            self.segment_stop_event.set()
        if self.segment_audio_thread:
            self.segment_audio_thread.join()
        start = self.segment_start_time.strftime("%d%b%Y_%H%M%S").lower()
        end_time = datetime.datetime.now()
        end = end_time.strftime("%d%b%Y_%H%M%S").lower()
        final_filename = os.path.join("Audios", f"audio_seg_{start}_to_{end}.wav")
        try:
            os.rename(self.segment_temp_file, final_filename)
        except Exception as e:
            print("Error renaming segmented audio file:", e)
            final_filename = self.segment_temp_file
        return final_filename

class VideoRecorder:
    def __init__(self, camera, audio_recorder=None):
        self.camera = camera
        self.audio_recorder = audio_recorder
        self.recording = False
        self.segment_threshold = 50 * 1024 * 1024
        self.current_video_file = None
        self.segments = []
        self.monitor_thread = None
        self.stop_monitor = False
        self.with_audio = False
        self.session_counter = 1
        self.chunk_num = 1
        self.video_start_time = None
        self.segmentation_thread = None
        self.current_segment_start = None

    def generate_video_filename(self):
        now = datetime.datetime.now()
        date_str = now.strftime("%d%b%Y").lower()
        time_str = now.strftime("%H%M%S")
        return os.path.join("Videos", f"temp_vdo_{date_str}_{time_str}.mp4")

    def start_recording(self, with_audio=False):
        if self.recording:
            return
        self.recording = True
        led_record_on()  # 🔁 Turn on LED when recording starts
        self.with_audio = with_audio
        self.segments.clear()
        os.makedirs("Videos", exist_ok=True)

        self.current_segment_start = datetime.datetime.now()

        if self.with_audio and self.audio_recorder:
            self.segmentation_thread = threading.Thread(
                target=self._record_with_segmentation, daemon=True
            )
            self.segmentation_thread.start()
        else:
            self.current_video_file = self.generate_video_filename()
            self.camera.apply_video_transform(hflip=True, vflip=False, rotation=90)
            self.camera.picam2.start_and_record_video(self.current_video_file)

            self.stop_monitor = False
            self.monitor_thread = threading.Thread(target=self.monitor_video_size, daemon=True)
            self.monitor_thread.start()

    def monitor_video_size(self):
        while self.recording and not self.stop_monitor:
            if os.path.exists(self.current_video_file):
                size = os.path.getsize(self.current_video_file)
                if size >= self.segment_threshold:
                    segment_end = datetime.datetime.now()
                    try:
                        self.camera.picam2.stop_recording()
                    except Exception as e:
                        print("Error stopping recording for segmentation:", e)

                    segment_record = {
                        "file": self.current_video_file,
                        "start": self.current_segment_start.strftime("%H:%M:%S"),
                        "end": segment_end.strftime("%H:%M:%S"),
                        "start_str": self.current_segment_start.strftime("%d%b%Y_%H%M%S").lower(),
                        "end_str": segment_end.strftime("%d%b%Y_%H%M%S").lower()
                    }
                    self.segments.append(segment_record)

                    self.current_segment_start = segment_end
                    self.current_video_file = self.generate_video_filename()
                    self.camera.picam2.start_and_record_video(self.current_video_file)

            time.sleep(1)

    def _record_with_segmentation(self):
        seg_start = self.current_segment_start
        while self.recording:
            video_file = self.generate_video_filename()
            self.camera.picam2.start_and_record_video(video_file)
            self.audio_recorder.start_segmented_recording()

            while self.recording:
                if os.path.exists(video_file) and os.path.getsize(video_file) >= self.segment_threshold:
                    break
                time.sleep(1)

            self.camera.picam2.stop_recording()
            seg_end = datetime.datetime.now()
            audio_file = self.audio_recorder.stop_segmented_recording()

            merged_file = self.merge_video_audio(video_file, audio_file, seg_start, seg_end, None)
            if merged_file:
                segment_record = {
                    "file": merged_file,
                    "start": seg_start.strftime("%H:%M:%S"),
                    "end": seg_end.strftime("%H:%M:%S"),
                    "start_str": seg_start.strftime("%d%b%Y_%H%M%S").lower(),
                    "end_str": seg_end.strftime("%d%b%Y_%H%M%S").lower()
                }
                self.segments.append(segment_record)
            else:
                segment_record = {
                    "file": video_file,
                    "start": seg_start.strftime("%H:%M:%S"),
                    "end": seg_end.strftime("%H:%M:%S"),
                    "start_str": seg_start.strftime("%d%b%Y_%H%M%S").lower(),
                    "end_str": seg_end.strftime("%d%b%Y_%H%M%S").lower()
                }
                self.segments.append(segment_record)

            self.chunk_num += 1
            seg_start = seg_end

    def merge_video_audio(self, video_file, audio_file, seg_start, seg_end, media_category):
        seg_start_str = seg_start.strftime("%d%b%Y_%H%M%S").lower()
        seg_end_str = seg_end.strftime("%d%b%Y_%H%M%S").lower()
        category_str = media_category if media_category else ""
        merged_file = os.path.join(
            "Videos",
            f"merged_{self.session_counter}_{self.chunk_num}_{seg_start_str}_to_{seg_end_str}_{category_str}.mp4"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-i", audio_file,
            "-c:v", "copy",
            "-c:a", "aac",
            merged_file
        ]
        try:
            subprocess.run(cmd, check=True)
            os.remove(video_file)
            os.remove(audio_file)
            return merged_file
        except subprocess.CalledProcessError as e:
            print("Error during merging:", e)
            return None

    def stop_recording(self, media_category):
        self.recording = False
        led_record_off()  # 🔁 Turn off LED when recording ends

        if self.with_audio and self.segmentation_thread is not None:
            self.segmentation_thread.join()
        else:
            self.stop_monitor = True
            if self.monitor_thread:
                self.monitor_thread.join()

            if self.current_video_file:
                seg_end = datetime.datetime.now()
                try:
                    self.camera.picam2.stop_recording()
                except Exception as e:
                    print("Error stopping video recording on final segment:", e)

                segment_record = {
                    "file": self.current_video_file,
                    "start": self.current_segment_start.strftime("%H:%M:%S"),
                    "end": seg_end.strftime("%H:%M:%S"),
                    "start_str": self.current_segment_start.strftime("%d%b%Y_%H%M%S").lower(),
                    "end_str": seg_end.strftime("%d%b%Y_%H%M%S").lower()
                }
                self.segments.append(segment_record)

        self.camera.picam2.start()

        final_segments = []
        prefix = "merged" if self.with_audio else "vdo"

        for idx, seg in enumerate(self.segments, start=1):
            final_name = os.path.join(
                "Videos",
                f"{prefix}_{self.session_counter}_{idx}_{seg['start_str']}_to_{seg['end_str']}_{media_category}.mp4"
            )
            try:
                os.rename(seg["file"], final_name)
            except Exception as e:
                print("Error renaming video file:", e)
                final_name = seg["file"]
            final_segments.append({
                "file": final_name,
                "start": seg["start"],
                "end": seg["end"]
            })

        self.session_counter += 1
        self.chunk_num = 1
        return final_segments
