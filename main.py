import js
import asyncio
import io
import base64
import random
from pyodide.ffi import create_proxy
from PIL import Image, ImageFilter

# --- GLOBÁLNE PREMENNÉ ---
original_image_data = None
current_blur = 50
score = 0
game_running = False

# Nastavenia hry
canvas = js.document.getElementById("snakeCanvas")
ctx = canvas.getContext("2d")
TILE_SIZE = 20
grid_size = 20
snake = [{"x": 10, "y": 10}]
direction = {"x": 1, "y": 0}
food = {"x": 15, "y": 15}

# Audio premenné
audio_ctx = None
bg_music = None
lowpass_filter = None

# --- 1. SPRACOVANIE OBRAZU ---
def update_image_display(blur_amount):
    if original_image_data is None: return
    
    # Aplikácia rozmazania cez Pillow
    if blur_amount > 0:
        modified_img = original_image_data.filter(ImageFilter.GaussianBlur(radius=blur_amount))
    else:
        modified_img = original_image_data

    buffered = io.BytesIO()
    modified_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    js.document.getElementById("image-overlay").src = f"data:image/png;base64,{img_str}"

def handle_upload(event):
    global original_image_data
    file = event.target.files.item(0)
    if not file: return

    async def process():
        array_buffer = await file.arrayBuffer()
        image_bytes = array_buffer.to_py()
        global original_image_data
        original_image_data = Image.open(io.BytesIO(image_bytes)).resize((400, 400))
        update_image_display(current_blur)
        js.document.getElementById("status").innerHTML = "Obrázok pripravený! Stlač šípku pre štart."

    asyncio.ensure_future(process())

# --- 2. AUDIO LOGIKA ---
def init_audio():
    global audio_ctx, bg_music, lowpass_filter
    try:
        audio_ctx = js.AudioContext.new()
        bg_music = js.Audio.new("music.mp3")
        bg_music.loop = True
        
        source = audio_ctx.createMediaElementSource(bg_music)
        lowpass_filter = audio_ctx.createBiquadFilter()
        lowpass_filter.type = "lowpass"
        lowpass_filter.frequency.value = 300 # Začíname tlmene
        
        source.connect(lowpass_filter)
        lowpass_filter.connect(audio_ctx.destination)
        bg_music.play()
    except Exception as e:
        print(f"Audio error: {e}")

def update_audio_clarity(current_score):
    if lowpass_filter:
        # Zvyšujeme frekvenciu filtra = čistejší zvuk
        new_freq = min(20000, 300 + (current_score * 1500))
        lowpass_filter.frequency.setTargetAtTime(new_freq, audio_ctx.currentTime, 0.1)

# --- 3. LOGIKA HRY ---
async def game_loop():
    global score, current_blur, game_running
    if not audio_ctx: init_audio()

    while game_running:
        new_head = {
            "x": snake[0]["x"] + direction["x"],
            "y": snake[0]["y"] + direction["y"]
        }

        # Kolízia so stenou alebo samým sebou
        if (new_head["x"] < 0 or new_head["x"] >= grid_size or 
            new_head["y"] < 0 or new_head["y"] >= grid_size or 
            new_head in snake):
            
            game_running = False
            js.Audio.new("gameover.mp3").play()
            if bg_music: bg_music.pause()
            js.alert(f"KONIEC HRY! Vaše skóre: {score}")
            break

        snake.insert(0, new_head)

        if new_head["x"] == food["x"] and new_head["y"] == food["y"]:
            score += 1
            current_blur = max(0, 50 - (score * 5))
            update_image_display(current_blur)
            update_audio_clarity(score)
            food["x"], food["y"] = random.randint(0, 19), random.randint(0, 19)
        else:
            snake.pop()

        # Vykreslenie
        ctx.clearRect(0, 0, 400, 400)
        ctx.fillStyle = "red" # Jedlo
        ctx.fillRect(food["x"]*20, food["y"]*20, 18, 18)
        ctx.fillStyle = "#00ff00" # Hadík
        for s in snake:
            ctx.fillRect(s["x"]*20, s["y"]*20, 18, 18)

        await asyncio.sleep(0.15)

def handle_keydown(event):
    global game_running, direction
    key = event.key
    if key == "ArrowUp" and direction["y"] == 0: direction = {"x": 0, "y": -1}
    elif key == "ArrowDown" and direction["y"] == 0: direction = {"x": 0, "y": 1}
    elif key == "ArrowLeft" and direction["x"] == 0: direction = {"x": -1, "y": 0}
    elif key == "ArrowRight" and direction["x"] == 0: direction = {"x": 1, "y": 0}
    
    if not game_running and original_image_data:
        game_running = True
        asyncio.ensure_future(game_loop())

# Registrácia eventov
js.document.getElementById("upload").addEventListener("change", create_proxy(handle_upload))
js.document.addEventListener("keydown", create_proxy(handle_keydown))