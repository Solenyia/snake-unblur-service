import js
import asyncio
import io
import base64
import random
from pyodide.ffi import create_proxy
from PIL import Image, ImageFilter

# --- KONFIGURÁCIA A PREMENNÉ ---
original_image_data = None
current_blur = 50
score = 0
game_running = False

# Nastavenia Canvasu
canvas = js.document.getElementById("snakeCanvas")
ctx = canvas.getContext("2d")
TILE_SIZE = 20
grid_size = 20 # 400 / 20

snake = [{"x": 10, "y": 10}]
direction = {"x": 1, "y": 0}
food = {"x": 15, "y": 15}

# Audio objekty
audio_ctx = None
bg_music = None
lowpass_filter = None

# --- MULTIMEDIÁLNE FUNKCIE (OBRAZ) ---
def update_image_display(blur_radius):
    if original_image_data is None: return
    
    # Pillow spracovanie
    img = original_image_data
    if blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    # Prevod do formátu pre HTML
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    js.document.getElementById("image-overlay").src = f"data:image/png;base64,{img_base64}"

async def handle_upload(event):
    global original_image_data
    file = event.target.files.item(0)
    if not file: return

    # Načítanie súboru
    array_buffer = await file.arrayBuffer()
    bytes_data = array_buffer.to_py()
    original_image_data = Image.open(io.BytesIO(bytes_data)).convert("RGB").resize((400, 400))
    
    update_image_display(current_blur)
    js.document.getElementById("status").innerHTML = "Pripravené! Ovládaj šípkami."

# --- MULTIMEDIÁLNE FUNKCIE (AUDIO) ---
def init_audio():
    global audio_ctx, bg_music, lowpass_filter
    try:
        audio_ctx = js.AudioContext.new()
        bg_music = js.Audio.new("music.mp3")
        bg_music.loop = True
        
        source = audio_ctx.createMediaElementSource(bg_music)
        lowpass_filter = audio_ctx.createBiquadFilter()
        lowpass_filter.type = "lowpass"
        lowpass_filter.frequency.value = 300 # Tlmený štart
        
        source.connect(lowpass_filter)
        lowpass_filter.connect(audio_ctx.destination)
        bg_music.play()
    except Exception as e:
        print(f"Audio init error: {e}")

def update_audio_clarity(s):
    if lowpass_filter:
        # Zvuk sa "vyostruje" zvyšovaním frekvencie
        new_freq = min(20000, 300 + (s * 1500))
        lowpass_filter.frequency.setTargetAtTime(new_freq, audio_ctx.currentTime, 0.2)

# --- JADRO HRY ---
async def game_loop():
    global score, current_blur, game_running
    if not audio_ctx: init_audio()

    while game_running:
        # Nová pozícia hlavy
        new_head = {
            "x": snake[0]["x"] + direction["x"],
            "y": snake[0]["y"] + direction["y"]
        }

        # KOLÍZIA (Stena alebo Telo)
        if (new_head["x"] < 0 or new_head["x"] >= grid_size or 
            new_head["y"] < 0 or new_head["y"] >= grid_size or 
            new_head in snake):
            
            game_running = False
            js.Audio.new("gameover.wav").play()
            if bg_music: bg_music.pause()
            js.alert(f"Game Over! Skóre: {score}")
            break

        snake.insert(0, new_head)

        # JEDENIE
        if new_head["x"] == food["x"] and new_head["y"] == food["y"]:
            score += 1
            current_blur = max(0, 50 - (score * 5))
            update_image_display(current_blur)
            update_audio_clarity(score)
            # Spawn nového jedla
            food["x"], food["y"] = random.randint(0, 19), random.randint(0, 19)
        else:
            snake.pop()

        # VYKRESLENIE
        ctx.clearRect(0, 0, 400, 400)
        
        # Jedlo
        ctx.fillStyle = "#ff4757"
        ctx.fillRect(food["x"]*TILE_SIZE, food["y"]*TILE_SIZE, TILE_SIZE-2, TILE_SIZE-2)
        
        # Hadík
        ctx.fillStyle = "#2ecc71"
        for part in snake:
            ctx.fillRect(part["x"]*TILE_SIZE, part["y"]*TILE_SIZE, TILE_SIZE-2, TILE_SIZE-2)

        await asyncio.sleep(0.15)

def on_keydown(event):
    global game_running, direction
    key = event.key
    if key == "ArrowUp" and direction["y"] == 0: direction = {"x": 0, "y": -1}
    elif key == "ArrowDown" and direction["y"] == 0: direction = {"x": 0, "y": 1}
    elif key == "ArrowLeft" and direction["x"] == 0: direction = {"x": -1, "y": 0}
    elif key == "ArrowRight" and direction["x"] == 0: direction = {"x": 1, "y": 0}
    
    if not game_running and original_image_data:
        game_running = True
        asyncio.ensure_future(game_loop())

# Event Listenery
js.document.getElementById("upload").addEventListener("change", create_proxy(handle_upload))
js.document.addEventListener("keydown", create_proxy(on_keydown))