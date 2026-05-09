import numpy as np
from scipy.io import wavfile

def generate_death_sound(filename="gameover.wav"):
    sample_rate = 44100
    duration = 0.5  # pol sekundy
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Frekvencia, ktorá klesá z 400 Hz na 100 Hz (klasický "sad" zvuk)
    frequency = np.linspace(400, 100, len(t))
    
    # Vygenerovanie vlny (pílovitý priebeh znie viac retro/8-bit)
    wave = 0.5 * (t * frequency % 1.0 - 0.5)
    
    # Fade-out efekt, aby to neklikalo na konci
    envelope = np.exp(-4 * t / duration)
    wave = wave * envelope

    # Prevod na 16-bit PCM
    wave_int = (wave * 32767).astype(np.int16)
    
    wavfile.write(filename, sample_rate, wave_int)
    print(f"Súbor {filename} bol úspešne vytvorený!")

if __name__ == "__main__":
    generate_death_sound()