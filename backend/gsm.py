import serial
import time
import pyttsx3
import os

# Update this to your serial port (e.g., '/dev/ttyUSB0' or 'COM3')
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

def send_sms(phone_number: str, message: str):
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(1)
        ser.write(b'AT+CMGF=1\r')
        time.sleep(0.5)
        ser.write(f'AT+CMGS="{phone_number}"\r'.encode())
        time.sleep(0.5)
        ser.write(message.encode() + b"\x1A")
        time.sleep(3)
        ser.close()
        print(f"SMS sent to {phone_number}")
    except Exception as e:
        print(f"Failed to send SMS: {e}")

def make_call(phone_number: str):
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(1)
        ser.write(f'ATD{phone_number};\r'.encode())
        time.sleep(30)  # Call duration
        ser.write(b'ATH\r')  # Hang up
        ser.close()
        print(f"Call made to {phone_number}")
    except Exception as e:
        print(f"Failed to make call: {e}")

def make_call_and_play_script(phone_number: str, script: str, audio_path: str = "tts_output.wav"):
    # Generate TTS audio
    engine = pyttsx3.init()
    engine.save_to_file(script, audio_path)
    engine.runAndWait()
    print(f"TTS audio generated at {audio_path}")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(1)
        ser.write(f'ATD{phone_number};\r'.encode())
        time.sleep(5)  # Wait for call to connect
        # Play audio file (assumes system audio is routed to GSM mic input)
        os.system(f'aplay {audio_path}')
        time.sleep(30)  # Call duration
        ser.write(b'ATH\r')  # Hang up
        ser.close()
        print(f"Call made to {phone_number} and script played.")
    except Exception as e:
        print(f"Failed to make call: {e}")
