import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import os
import random
import time

# --- グローバル変数 ---
start_time = None
timer_id = None
ranking_file = "ranking.txt"
grid_size = 0
piece_size = 0

# --- タイマー更新 ---
def update_timer():
    global start_time, timer_id
    elapsed = int(time.time() - start_time)
    mins, secs = divmod(elapsed, 60)
    timer_label.config(text=f"経過時間: {mins}分{secs:02}秒")
    timer_id = root.after(1000, update_timer)

# --- パズル初期化＋タイマー開始 ---
def start_puzzle():
    global start_time, timer_id, puzzle_origin_x, puzzle_origin_y, puzzle_size

    # タイマー開始
    if timer_id:
        root.after_cancel(timer_id)
    start_time = time.time()
    update_timer()

    canvas.delete("all")
    canvas.images.clear()
    canvas.piece_infos.clear()
    canvas.solved_count = 0

    selected_img = image_var.get()
    selected_level = level_var.get()
    if selected_img and selected_level:
        path = os.path.join(".", selected_img)
        grid_size = int(selected_level)

        # パズルサイズと位置
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        puzzle_size = min(canvas_width // 2, canvas_height - 100)
        puzzle_origin_x = (canvas_width - puzzle_size) // 2
        puzzle_origin_y = (canvas_height - puzzle_size) // 2

        img = Image.open(path).convert("RGBA").resize((puzzle_size, puzzle_size))

        pieces, piece_infos = create_pieces(img, grid_size)

        for i, piece in enumerate(pieces):
            # ピース配置（外周ランダム）
            if random.choice([True, False]):
                x = random.randint(50, canvas_width - 50 - puzzle_size)
                y = random.choice([50, canvas_height - 100])
            else:
                x = random.choice([50, canvas_width - 100])
                y = random.randint(50, canvas_height - 50 - puzzle_size)

            pid = canvas.create_image(x, y, anchor="nw", image=piece, tags="draggable")
            canvas.images.append(piece)
            canvas.piece_infos[pid] = piece_infos[i]

        draw_slots(grid_size, pw)

# --- ランキング更新 ---
def update_ranking(new_time):
    if not os.path.exists(ranking_file):
        open(ranking_file, "w").close()
    with open(ranking_file, "r") as f:
        times = [int(l.strip()) for l in f if l.strip().isdigit()]
    times.append(new_time)
    times.sort()
    with open(ranking_file, "w") as f:
        for t in times[:10]:
            m, s = divmod(t, 60)
            f.write(f"{m}分{s:02}秒\n")

# --- 外枠線の描画 ---
def draw_slots():
    global grid_size, piece_size
    for row in range(grid_size):
        for col in range(grid_size):
            x = puzzle_origin_x + col * piece_size
            y = puzzle_origin_y + row * piece_size
            canvas.create_rectangle(x, y, x + piece_size, y + piece_size, outline="black", width=2)

# --- メインGUI ---
root = tk.Tk()
root.title("CMB ジグソーパズル")
root.state("zoomed")

# 経過タイム表示
timer_label = ttk.Label(root, text="経過時間: 0分00秒", font=("Arial", 16))
timer_label.pack()

# 画像・レベル選択
image_var = tk.StringVar()
level_var = tk.StringVar()
image_list = [f for f in os.listdir(".") if f.lower().endswith((".jpg", ".png"))]

ttk.Label(root, text="画像選択:").pack()
image_combo = ttk.Combobox(root, textvariable=image_var, values=image_list)
image_combo.pack()

ttk.Label(root, text="レベル:").pack()
level_combo = ttk.Combobox(root, textvariable=level_var, values=["3", "4", "5"])
level_combo.pack()

start_btn = ttk.Button(root, text="スタート", command=start_puzzle)
start_btn.pack()

# Canvas (全画面)
canvas = tk.Canvas(root, bg="lightgray")
canvas.pack(fill="both", expand=True)
canvas.images = []
canvas.piece_infos = {}
canvas.solved_count = 0

# フルスクリーン設定
root.state("zoomed")  # Windowsで全画面
# root.attributes('-fullscreen', True)  # Mac/Linuxならこちら

#1
# ---------- ジグソーピース形状生成 ----------
def create_piece_mask(size, top, right, bottom, left):
    w, h = size
    p = int(min(w, h) * 0.25)  # 突起サイズ
    r = p // 2  # 円弧半径
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)

    # 基本の矩形
    draw.rectangle((0, 0, w, h), fill=255)

    # 円弧の描画関数
    def draw_tab(x, y, direction, axis):
        bbox = None
        if axis == "h":  # 水平（上or下）
            bbox = (x - r, y - r, x + r, y + r)
            if direction == 1:  # 凸
                draw.pieslice(bbox, 0, 180, fill=255)
            else:  # 凹
                draw.pieslice(bbox, 0, 180, fill=0)
        else:  # 垂直（左or右）
            bbox = (x - r, y - r, x + r, y + r)
            if direction == 1:
                draw.pieslice(bbox, 270, 90, fill=255)
            else:
                draw.pieslice(bbox, 270, 90, fill=0)

    # 上
    if top != 0:
        draw_tab(w//2, 0, top, "h")
    # 右
    if right != 0:
        draw_tab(w, h//2, right, "v")
    # 下
    if bottom != 0:
        draw_tab(w//2, h, bottom, "h")
    # 左
    if left != 0:
        draw_tab(0, h//2, left, "v")

    return mask


#2
# ---------- ピース生成 ----------
def create_pieces(img, grid_size):
    w, h = img.size
    pw, ph = w // grid_size, h // grid_size
    pieces = []
    piece_infos = []

    # 隣接するピース同士で突起・凹みが噛み合うように形状を決定
    shapes = {}
    for row in range(grid_size):
        for col in range(grid_size):
            top = 0 if row == 0 else -shapes[(row-1, col)][2]
            left = 0 if col == 0 else -shapes[(row, col-1)][1]
            right = random.choice([-1, 1]) if col < grid_size - 1 else 0
            bottom = random.choice([-1, 1]) if row < grid_size - 1 else 0
            shapes[(row, col)] = (top, right, bottom, left)

    # ピースごとにマスクして切り出し
    for row in range(grid_size):
        for col in range(grid_size):
            box = (col * pw, row * ph, (col + 1) * pw, (row + 1) * ph)
            top, right, bottom, left = shapes[(row, col)]
            mask = create_piece_mask((pw, ph), top, right, bottom, left)
            piece = img.crop(box).copy()
            piece.putalpha(mask)
            pieces.append(ImageTk.PhotoImage(piece))
            piece_infos.append({
                "row": row,
                "col": col,
                "correct_x": col * pw + puzzle_origin_x,
                "correct_y": row * ph + puzzle_origin_y,
            })
    return pieces, piece_infos

#3
# ---------- ドラッグ操作 ----------
def on_start_drag(event):
    item = canvas.find_closest(event.x, event.y)[0]
    canvas.drag_data = {
        "item": item,
        "x": event.x,
        "y": event.y
    }

def on_drag(event):
    dx = event.x - canvas.drag_data["x"]
    dy = event.y - canvas.drag_data["y"]
    canvas.move(canvas.drag_data["item"], dx, dy)
    canvas.drag_data["x"] = event.x
    canvas.drag_data["y"] = event.y

def on_drop(event):
    item = canvas.drag_data["item"]
    x, y = canvas.coords(item)
    info = canvas.piece_infos[item]

    # 近ければスナップ
    if abs(x - info["correct_x"]) < 20 and abs(y - info["correct_y"]) < 20:
        canvas.coords(item, info["correct_x"], info["correct_y"])
        canvas.solved_count += 1

    if canvas.solved_count == len(canvas.piece_infos):
        canvas.create_text(canvas.winfo_width()//2, canvas.winfo_height()//2, text="完成!", fill="red", font=("Arial", 50))

# イベント
canvas.bind("<Button-1>", on_start_drag)
canvas.bind("<B1-Motion>", on_drag)
canvas.bind("<ButtonRelease-1>", on_drop)

#4
# ---------- パズル初期化 ----------
def start_puzzle():
    global start_time, timer_id, puzzle_origin_x, puzzle_origin_y, puzzle_size, grid_size, piece_size
    canvas.delete("all")
    canvas.images.clear()
    canvas.piece_infos.clear()
    canvas.solved_count = 0

    selected_img = image_var.get()
    selected_level = level_var.get()
    if selected_img and selected_level:
        path = os.path.join(".", selected_img)
        grid_size = int(selected_level)

        # パズル領域
        global puzzle_origin_x, puzzle_origin_y, puzzle_size
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        puzzle_size = min(canvas_width // 2, canvas_height - 100)
        puzzle_origin_x = (canvas_width - puzzle_size) // 2
        puzzle_origin_y = (canvas_height - puzzle_size) // 2

        img = Image.open(path).convert("RGBA").resize((puzzle_size, puzzle_size))

        pieces, piece_infos = create_pieces(img, grid_size)

        # ランダムにパズル外に配置
        for i, piece in enumerate(pieces):
            # 上 or 下
            if random.choice([True, False]):
                x = random.randint(50, canvas_width - 50 - puzzle_size)
                y = random.choice([50, canvas_height - 100])
            else:  # 左 or 右
                x = random.choice([50, canvas_width - 100])
                y = random.randint(50, canvas_height - 50 - puzzle_size)

            pid = canvas.create_image(x, y, anchor="nw", image=piece, tags="draggable")
            canvas.images.append(piece)
            canvas.piece_infos[pid] = piece_infos[i]

#5
# --- クリア時処理 ---
def on_clear():
    global timer_id
    root.after_cancel(timer_id)  # タイマー停止
    elapsed = int(time.time() - start_time)
    mins, secs = divmod(elapsed, 60)

    # --- ランキング更新 ---
    update_ranking(elapsed)

    # --- クリア画面表示 ---
    result = tk.Toplevel(root)
    result.title("クリア！")
    ttk.Label(result, text=f"おめでとう！タイム: {mins}分{secs:02}秒").pack()
    ttk.Label(result, text="ランキング:").pack()

    # --- ランキング表示 ---
    with open(ranking_file, "r") as f:
        lines = f.readlines()
    for line in lines[:10]:
        ttk.Label(result, text=line.strip()).pack()

root.mainloop()
