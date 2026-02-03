import serial
import threading
import queue
import tkinter as tk
from tkinter import simpledialog
from datetime import datetime
import winsound

# ---------------- CONFIG ----------------
PORT = "COM3"      # <-- ändra till din Arduino-port
BAUD = 115200
# ----------------------------------------

lap_queue = queue.Queue()

# ---------- SOUND HELPERS (Windows) ----------

def play_lap_beep():
    winsound.PlaySound("beep_lap.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)

def play_best_beep():
    winsound.PlaySound("beep_best.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)

def play_finish_beep():
    winsound.PlaySound("beep_finish.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)

def play_countdown_beep():
    winsound.PlaySound("beep_countdown.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)

# ---------- SERIAL READER ----------

def serial_reader():
    """Background thread: read lines from Arduino and push lap times into queue."""
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except:
        # Ingen Arduino inkopplad – kör GUI ändå
        return

    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        try:
            ms = int(line)
        except ValueError:
            continue
        if ms < 50:
            continue
        lap_queue.put(ms / 1000.0)

# ---------- MAIN MENU ----------

class MainMenu:
    def __init__(self, root):
        self.root = root
        self.root.title("RC Lap Manager")

        self.drivers = {}   # name -> list of lap times
        self.target_laps = 5
        self.current_heat = 1

        self.font_title = ("Helvetica", 30, "bold")
        self.font_normal = ("Helvetica", 20)

        self.build_ui()

    def build_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=10)

        self.label_heat = tk.Label(top_frame, text=f"Heat: {self.current_heat}", font=self.font_title)
        self.label_heat.pack(side=tk.LEFT, padx=20)

        tk.Button(top_frame, text="Next Heat", font=self.font_normal,
                  command=self.next_heat).pack(side=tk.LEFT, padx=20)

        tk.Label(self.root, text="Driver List", font=self.font_title).pack(pady=10)

        self.driver_listbox = tk.Listbox(self.root, font=self.font_normal, width=30, height=10)
        self.driver_listbox.pack(pady=10)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Add Driver", font=self.font_normal,
                  command=self.add_driver).pack(side=tk.LEFT, padx=10)

        tk.Button(btn_frame, text="Set Laps", font=self.font_normal,
                  command=self.set_laps).pack(side=tk.LEFT, padx=10)

        tk.Button(btn_frame, text="Start Race", font=self.font_normal,
                  command=self.start_race).pack(side=tk.LEFT, padx=10)

        self.results_label = tk.Label(self.root, text="", font=self.font_normal, justify=tk.LEFT)
        self.results_label.pack(pady=20)

    def add_driver(self):
        name = simpledialog.askstring("Driver Name", "Enter driver name:")
        if name:
            if name not in self.drivers:
                self.drivers[name] = []
                self.driver_listbox.insert(tk.END, name)

    def set_laps(self):
        laps = simpledialog.askinteger("Laps", "Enter number of laps:")
        if laps and laps > 0:
            self.target_laps = laps

    def start_race(self):
        selection = self.driver_listbox.curselection()
        if not selection:
            return
        driver = self.driver_listbox.get(selection[0])
        RaceApp(self.root, driver, self.target_laps, self.current_heat, self.finish_race)

    def finish_race(self, driver, laps, heat_number):
        self.drivers[driver] = laps
        self.save_results_to_file(heat_number)
        self.show_results()

    def show_results(self):
        text = f"=== RESULTS (Heat {self.current_heat}) ===\n"
        for name, laps in self.drivers.items():
            if laps:
                best = min(laps)
                text += f"{name}: best {best:.3f}s, laps: {len(laps)}\n"
        self.results_label.config(text=text)

    def save_results_to_file(self, heat_number):
        filename = f"results_heat_{heat_number}.txt"
        lines = []
        lines.append(f"Results for Heat {heat_number}")
        lines.append(f"Date/Time: {datetime.now().isoformat()}")
        lines.append("")

        for name, laps in self.drivers.items():
            if laps:
                best = min(laps)
                lines.append(f"Driver: {name}")
                lines.append(f"  Best lap: {best:.3f}s")
                lines.append(f"  Laps ({len(laps)}):")
                for i, t in enumerate(laps, start=1):
                    lines.append(f"    {i}. {t:.3f}s")
                lines.append("")

        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def next_heat(self):
        self.current_heat += 1
        self.label_heat.config(text=f"Heat: {self.current_heat}")
        for name in self.drivers:
            self.drivers[name] = []
        self.results_label.config(text="")

# ---------- RACE APP ----------

class RaceApp:
    def __init__(self, root, driver, target_laps, heat_number, callback):
        self.root = root
        self.driver = driver
        self.target_laps = target_laps
        self.heat_number = heat_number
        self.callback = callback

        self.laps = []
        self.best_lap = None

        self.window = tk.Toplevel(root)
        self.window.attributes("-fullscreen", True)
        self.window.bind("<Escape>", self.exit_race)

        self.font_big = ("Helvetica", 80, "bold")
        self.font_med = ("Helvetica", 40)
        self.font_small = ("Helvetica", 25)

        self.build_ui()

        self.countdown_value = 3
        self.show_countdown()

    def build_ui(self):
        tk.Label(self.window, text=f"Heat {self.heat_number}", font=self.font_med).pack(pady=10)
        tk.Label(self.window, text=f"Driver: {self.driver}", font=self.font_med).pack(pady=10)

        self.label_laps = tk.Label(self.window, text=f"Laps: 0 / {self.target_laps}", font=self.font_med)
        self.label_laps.pack(pady=10)

        self.label_main = tk.Label(self.window, text="", font=self.font_big)
        self.label_main.pack(pady=20)

        self.label_best = tk.Label(self.window, text="Best: ---.---", font=self.font_med)
        self.label_best.pack(pady=10)

        self.label_list = tk.Label(self.window, text="", font=self.font_small, justify=tk.LEFT)
        self.label_list.pack(pady=20)

    # ----- COUNTDOWN -----

    def show_countdown(self):
        if self.countdown_value > 0:
            self.label_main.config(text=str(self.countdown_value))
            play_countdown_beep()
            self.countdown_value -= 1
            self.window.after(1000, self.show_countdown)
        else:
            self.label_main.config(text="GO!")
            play_best_beep()
            self.window.after(500, self.start_race)

    def start_race(self):
        self.label_main.config(text="Last: ---.---")
        self.window.after(50, self.check_laps)

    # ----- LAP HANDLING -----

    def check_laps(self):
        updated = False
        while not lap_queue.empty():
            lap = lap_queue.get()
            self.add_lap(lap)
            updated = True

        if updated:
            self.update_display()

        if len(self.laps) >= self.target_laps:
            self.finish_race()
            return

        self.window.after(50, self.check_laps)

    def add_lap(self, lap):
        self.laps.append(lap)
        if self.best_lap is None or lap < self.best_lap:
            self.best_lap = lap
            play_best_beep()
        else:
            play_lap_beep()

    def update_display(self):
        self.label_laps.config(text=f"Laps: {len(self.laps)} / {self.target_laps}")

        if self.laps:
            last = self.laps[-1]
            self.label_main.config(text=f"Last: {last:.3f}")
            self.label_best.config(text=f"Best: {self.best_lap:.3f}")

            sorted_laps = sorted(self.laps)
            text = "\n".join([f"{i+1}. {t:.3f}" for i, t in enumerate(sorted_laps)])
            self.label_list.config(text=text)

    def finish_race(self):
        play_finish_beep()
        self.window.after(1000, self._close_and_callback)

    def _close_and_callback(self):
        self.window.destroy()
        self.callback(self.driver, self.laps, self.heat_number)

    def exit_race(self, event=None):
        self.window.destroy()

# ---------- MAIN ----------

if __name__ == "__main__":
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

    root = tk.Tk()
    app = MainMenu(root)
    root.mainloop()
