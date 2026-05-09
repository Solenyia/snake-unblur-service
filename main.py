import js
from pyodide.ffi import create_proxy
from PIL import Image, ImageFilter
import io
import base64

# Globálne premenné pre hru a obrázok
original_image_data = None
current_blur = 50

def handle_upload(event):
    global original_image_data
    
    # Získanie súboru z inputu
    file_list = event.target.files
    if len(file_list) == 0:
        return
        
    file = file_list.item(0)
    
    # Prečítanie súboru ako array buffer
    def process_file(data):
        global original_image_data
        image_bytes = data.to_py()
        original_image_data = Image.open(io.BytesIO(image_bytes))
        update_image_display(current_blur)

    # PyScript/Pyodide asynchrónne čítanie
    file.arrayBuffer().then(create_proxy(process_file))

def update_image_display(blur_amount):
    if original_image_data is None:
        return

    # Aplikácia rozmazania
    if blur_amount > 0:
        modified_img = original_image_data.filter(ImageFilter.GaussianBlur(radius=blur_amount))
    else:
        modified_img = original_image_data

    # Prevod na base64 pre HTML <img> tag
    buffered = io.BytesIO()
    modified_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Aktualizácia elementu v HTML
    js.document.getElementById("image-overlay").src = f"data:image/png;base64,{img_str}"

# Registrácia eventu pre upload
upload_element = js.document.getElementById("upload")
upload_proxy = create_proxy(handle_upload)
upload_element.addEventListener("change", upload_proxy)

import asyncio

# Nastavenia hry
canvas = js.document.getElementById("snakeCanvas")
ctx = canvas.getContext("2d")
TILE_SIZE = 20
grid_size = 20 # 400 / 20

snake = [{"x": 10, "y": 10}]
direction = {"x": 1, "y": 0}
food = {"x": 15, "y": 15}
score = 0
game_running = False

def draw_rect(x, y, color):
    ctx.fillStyle = color
    ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE - 2, TILE_SIZE - 2)

async def game_loop():
    global score, current_blur, game_running
    
    while game_running:
        # 1. Pohyb hada
        new_head = {
            "x": (snake[0]["x"] + direction["x"]) % grid_size,
            "y": (snake[0]["y"] + direction["y"]) % grid_size
        }
        
        # 2. Kontrola kolízie so sebou
        if new_head in snake:
            js.alert(f"Koniec hry! Tvoje skóre: {score}")
            game_running = False
            break

        snake.insert(0, new_head)

        # 3. Kontrola jedla
        if new_head["x"] == food["x"] and new_head["y"] == food["y"]:
            score += 1
            # WOW EFEKT: Zníženie blur-u [cite: 31]
            current_blur = max(0, 50 - (score * 5)) 
            update_image_display(current_blur)
            spawn_food()
        else:
            snake.pop()

        # 4. Vykresľovanie
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        draw_rect(food["x"], food["y"], "red") # Jedlo
        for segment in snake:
            draw_rect(segment["x"], segment["y"], "#00FF00") # Hadík
        
        await asyncio.sleep(0.15) # Rýchlosť hry

def spawn_food():
    import random
    food["x"] = random.randint(0, grid_size - 1)
    food["y"] = random.randint(0, grid_size - 1)

# Ovládanie klávesnicou
def handle_keydown(event):
    global game_running
    key = event.key
    if key == "ArrowUp" and direction["y"] == 0: direction["x"], direction["y"] = 0, -1
    elif key == "ArrowDown" and direction["y"] == 0: direction["x"], direction["y"] = 0, 1
    elif key == "ArrowLeft" and direction["x"] == 0: direction["x"], direction["y"] = -1, 0
    elif key == "ArrowRight" and direction["x"] == 0: direction["x"], direction["y"] = 1, 0
    
    if not game_running and original_image_data:
        game_running = True
        asyncio.ensure_future(game_loop())

js.document.addEventListener("keydown", create_proxy(handle_keydown))