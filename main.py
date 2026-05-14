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
audio_ctx = None
particles = []

canvas = js.document.getElementById("snakeCanvas")
ctx = canvas.getContext("2d")
TILE_SIZE = 20

snake = [{"x": 10, "y": 10}]
direction = {"x": 1, "y": 0}
food = {"x": 15, "y": 15}
trap = {"x": 5, "y": 5} # "Glitch" spomalovač/rozostrovač

# --- POMOCNÉ FUNKCIE ---
def log_message(msg):
    log_el = js.document.getElementById("live-log")
    current_content = log_el.innerHTML.split("<br>")[-2:] # Držať posledné 2 riadky
    log_el.innerHTML = "<br>".join(current_content) + f"<br>> {msg}"

def play_tone(freq, dur=0.1, type="square"):
    global audio_ctx
    if not audio_ctx: audio_ctx = js.AudioContext.new()
    o, g = audio_ctx.createOscillator(), audio_ctx.createGain()
    o.type = type
    o.frequency.setValueAtTime(freq, audio_ctx.currentTime)
    g.gain.setValueAtTime(0.05, audio_ctx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.0001, audio_ctx.currentTime + dur)
    o.connect(g); g.connect(audio_ctx.destination)
    o.start(); o.stop(audio_ctx.currentTime + dur)

def update_display():
    if original_image_data:
        img = original_image_data.filter(ImageFilter.GaussianBlur(radius=current_blur))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        js.document.getElementById("image-overlay").src = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    js.document.getElementById("score-val").innerHTML = f"{score:02d}"
    js.document.getElementById("blur-val").innerHTML = f"{max(0, int((50-current_blur)/50*100))}%"

# --- EVENT HANDLERY ---
async def handle_upload(event):
    global original_image_data
    file = event.target.files.item(0)
    if not file: return
    log_message("INJECTING_DATA_STREAM...")
    data = await file.arrayBuffer()
    original_image_data = Image.open(io.BytesIO(data.to_py())).convert("RGB").resize((400, 400))
    update_display()
    log_message("DECRYPTION_READY_STBY")

async def game_loop():
    global score, current_blur, game_running, food, trap
    container = js.document.getElementById("game-container")
    
    while game_running:
        new_head = {"x": snake[0]["x"] + direction["x"], "y": snake[0]["y"] + direction["y"]}

        # KOLÍZIA
        if (new_head["x"] < 0 or new_head["x"] >= 20 or new_head["y"] < 0 or new_head["y"] >= 20 or any(p == new_head for p in snake)):
            play_tone(80, 0.5, "sawtooth")
            container.classList.add("glitch")
            log_message("CRITICAL_FAILURE_REBOOT")
            await asyncio.sleep(1)
            container.classList.remove("glitch")
            reset_game(); break

        snake.insert(0, new_head)

        # JEDENIE JABLKA (DOBRÉ)
        if new_head == food:
            score += 1
            play_tone(400 + score*20, 0.1, "triangle")
            current_blur = max(0, current_blur - 5)
            update_display()
            log_message(f"SECTOR_{score}_DECRYPTED")
            food = {"x": random.randint(0, 19), "y": random.randint(0, 19)}
            # Premiestniť pascu
            trap = {"x": random.randint(0, 19), "y": random.randint(0, 19)}
        
        # JEDENIE PASCE (ZLE - SPOMALENIE A ROZOSTRENIE)
        elif new_head == trap:
            play_tone(150, 0.3, "sine")
            current_blur = min(50, current_blur + 10) # Rozostriť späť
            update_display()
            log_message("GLITCH_DETECTED_INTEGRITY_DROP")
            trap = {"x": -1, "y": -1} # Zmizne po zjedení
        else:
            snake.pop()

        # RENDER
        ctx.clearRect(0, 0, 400, 400)
        neon = js.getComputedStyle(js.document.documentElement).getPropertyValue('--neon').strip()
        
        # Jablko (Neon)
        ctx.shadowBlur = 15; ctx.shadowColor = neon
        ctx.fillStyle = neon; ctx.fillRect(food["x"]*20+4, food["y"]*20+4, 12, 12)
        
        # Pasca (Glitch fialová)
        ctx.shadowColor = "#ff00ff"
        ctx.fillStyle = "#ff00ff"
        ctx.fillRect(trap["x"]*20+6, trap["y"]*20+6, 8, 8)
        
        # Had
        ctx.shadowColor = "white"
        for i, p in enumerate(snake):
            ctx.fillStyle = "white" if i == 0 else neon
            ctx.fillRect(p["x"]*20+1, p["y"]*20+1, 18, 18)
        
        ctx.shadowBlur = 0
        await asyncio.sleep(max(0.06, 0.15 - (score * 0.005)))

def reset_game():
    global snake, direction, score, current_blur, game_running
    snake = [{"x": 10, "y": 10}]; direction = {"x": 1, "y": 0}
    score = 0; current_blur = 50; game_running = False; update_display()

def on_keydown(event):
    global game_running, direction
    moves = {"ArrowUp": (0, -1), "ArrowDown": (0, 1), "ArrowLeft": (-1, 0), "ArrowRight": (1, 0)}
    if event.key in moves:
        v = moves[event.key]
        if (v[0]*-1 != direction["x"]) or (v[1]*-1 != direction["y"]):
            direction = {"x": v[0], "y": v[1]}
        if not game_running and original_image_data:
            game_running = True; asyncio.ensure_future(game_loop())

js.document.getElementById("upload").addEventListener("change", create_proxy(handle_upload))
js.document.addEventListener("keydown", create_proxy(on_keydown))