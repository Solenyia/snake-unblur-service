import js
import asyncio
import io
import base64
import random
from pyodide.ffi import create_proxy
from PIL import Image, ImageFilter

# --- CONFIG ---
original_image_data = None
current_blur = 50
score = 0
game_running = False
audio_ctx = None
particles = []

canvas = js.document.getElementById("snakeCanvas")
ctx = canvas.getContext("2d")

snake = [{"x": 10, "y": 10}]
direction = {"x": 1, "y": 0}
food = {"x": 15, "y": 15}

async def matrix_effect(text):
    el = js.document.getElementById("status")
    c = "X01"
    for i in range(len(text) + 1):
        el.innerHTML = text[:i] + "".join(random.choice(c) for _ in range(5))
        await asyncio.sleep(0.03)
    el.innerHTML = text

def play_sound(freq, dur=0.15, type="square"):
    global audio_ctx
    if not audio_ctx: audio_ctx = js.AudioContext.new()
    now = audio_ctx.currentTime
    o, g = audio_ctx.createOscillator(), audio_ctx.createGain()
    o.type = type
    o.frequency.setValueAtTime(freq, now)
    g.gain.setValueAtTime(0.06, now)
    g.gain.exponentialRampToValueAtTime(0.0001, now + dur)
    o.connect(g); g.connect(audio_ctx.destination)
    o.start(); o.stop(now + dur)

class P:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx, self.vy = random.uniform(-4, 4), random.uniform(-4, 4)
        self.life = 1.0

def update_v():
    if original_image_data:
        img = original_image_data.filter(ImageFilter.GaussianBlur(radius=current_blur))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        js.document.getElementById("image-overlay").src = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    js.document.getElementById("score-val").innerHTML = f"{score:02d}"
    integrity = int(((50 - current_blur) / 50) * 100)
    js.document.getElementById("blur-val").innerHTML = f"{max(0, integrity)}%"

async def handle_upload(event):
    global original_image_data
    file = event.target.files.item(0)
    if not file: return
    await matrix_effect("INJECTING_PAYLOAD...")
    data = await file.arrayBuffer()
    original_image_data = Image.open(io.BytesIO(data.to_py())).convert("RGB").resize((400, 400))
    update_v()
    await matrix_effect("READY: PRESS ANY ARROW")

async def game_loop():
    global score, current_blur, game_running, food
    cont = js.document.getElementById("game-container")
    while game_running:
        head = {"x": snake[0]["x"] + direction["x"], "y": snake[0]["y"] + direction["y"]}
        if head["x"] < 0 or head["x"] >= 20 or head["y"] < 0 or head["y"] >= 20 or any(p == head for p in snake):
            play_sound(60, 0.5, "sawtooth")
            cont.classList.add("glitch")
            await matrix_effect("CRITICAL_ERROR: RETRYING")
            cont.classList.remove("glitch")
            reset_game(); break
        snake.insert(0, head)
        if head == food:
            score += 1
            for _ in range(10): particles.append(P(food["x"]*20+10, food["y"]*20+10))
            play_sound(500 + (score*20), 0.1, "triangle")
            current_blur = max(0, 50 - (score*5))
            update_v()
            food = {"x": random.randint(0, 19), "y": random.randint(0, 19)}
        else: snake.pop()
        
        ctx.clearRect(0, 0, 400, 400)
        neon = js.getComputedStyle(js.document.documentElement).getPropertyValue('--neon').strip()
        
        # Jablko
        ctx.shadowBlur = 15; ctx.shadowColor = neon
        ctx.strokeStyle = neon; ctx.lineWidth = 2
        ctx.strokeRect(food["x"]*20+5, food["y"]*20+5, 10, 10)
        
        # Hadík
        for i, p in enumerate(snake):
            ctx.fillStyle = "#fff" if i == 0 else neon
            ctx.fillRect(p["x"]*20+1, p["y"]*20+1, 18, 18)
        
        # Častice
        for p in particles[:]:
            p.x += p.vx; p.y += p.vy; p.life -= 0.05
            if p.life <= 0: particles.remove(p)
            else:
                ctx.fillStyle = f"rgba(255,255,255,{p.life})"
                ctx.fillRect(p.x, p.y, 2, 2)
        
        ctx.shadowBlur = 0
        await asyncio.sleep(max(0.05, 0.14 - (score * 0.007)))

def reset_game():
    global snake, direction, score, current_blur, game_running
    snake = [{"x": 10, "y": 10}]; direction = {"x": 1, "y": 0}
    score = 0; current_blur = 50; game_running = False; update_v()

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