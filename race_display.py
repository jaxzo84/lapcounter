import serial
import threading
import queue
import tkinter as tk

# ---------- CONFIG ----------
PORT = "COM3"      # <-- change this to your Arduino port
BAUD = 115200

ACTIVE_DRIVER = "Adam"
TARGET_LAPS = 5
# ----------------------------

drivers = {
    ACTIVE_DRIVER: {
        "laps": [],
        "target_laps": TARGET_LAPS
    }
}

lap_queue = queue.Queue()

def serial_reader():
    """Background thread: read lines from Arduino and push lap times into queue."""
    ser = serial.Serial(PORT, BAUD, timeout=1)
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue
        try:
            ms = int(line)
        except ValueError:
            # Ignore non-numeric lines
            continue

        if ms < 50:
            # Ignore tiny glitches
            continue

        lap_sec = ms / 1000.0
        lap_queue.put(lap_sec)

class RaceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RC Lap Counter")

        # Fullscreen
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", self.exit_fullscreen)

        self.driver_name = ACTIVE_DRIVER

        # Fonts
        self.font_title = ("Helvetica", 40, "bold")
        self.font_big = ("Helvetica", 80, "bold")
        self.font_medium = ("Helvetica", 30)
        self.font_small = ("Helvetica", 20)

        self.build_layout()
        self.root.after(100, self.check_lap_queue)

    def build_layout(self):
        # Top: driver + lap count
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=20)

        self.label_driver = tk.Label(
            top_frame,
            text=f"Driver: {self.driver_name}",
            font=self.font_title
        )
        self.label_driver.pack(side=tk.LEFT, padx=40)

        self.label_laps = tk.Label(
            top_frame,
            text=f"Laps: 0 / {drivers[self.driver_name]['target_laps']}",
            font=self.font_title
        )
        self.label_laps.pack(side=tk.LEFT, padx=40)

        # Middle: last lap + best lap
        middle_frame = tk.Frame(self.root)
        middle_frame.pack(pady=40)

        self.label_last = tk.Label(
            middle_frame,
            text="Last lap: ---.--- s",
            font=self.font_big
        )
        self.label_last.pack(pady=20)

        self.label_best = tk.Label(
            middle_frame,
            text="Best lap: ---.--- s",
            font=self.font_big
        )
        self.label_best.pack(pady=20)

        # Bottom: list of laps sorted
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(pady=20, fill=tk.BOTH, expand=True)

        self.label_list_title = tk.Label(
            bottom_frame,
            text="Laps (best → worst)",
            font=self.font_medium
        )
        self.label_list_title.pack()

        self.label_lap_list = tk.Label(
            bottom_frame,
            text="No laps yet",
            font=self.font_small,
            justify=tk.LEFT
        )
        self.label_lap_list.pack(pady=10)

        self.label_hint = tk.Label(
            self.root,
            text="Press ESC to exit",
            font=self.font_small
        )
        self.label_hint.pack(side=tk.BOTTOM, pady=10)

    def check_lap_queue(self):
        updated = False
        while not lap_queue.empty():
            lap_sec = lap_queue.get()
            self.add_lap(self.driver_name, lap_sec)
            updated = True

        if updated:
            self.update_display()

        self.root.after(50, self.check_lap_queue)

    def add_lap(self, driver, lap_sec):
        drivers[driver]["laps"].append(lap_sec)

    def update_display(self):
        d = drivers[self.driver_name]
        laps = d["laps"]
        target = d["target_laps"]

        self.label_laps.config(
            text=f"Laps: {len(laps)} / {target}"
        )

        if laps:
            last = laps[-1]
            best = min(laps)

            self.label_last.config(text=f"Last lap: {last:0.3f} s")
            self.label_best.config(text=f"Best lap: {best:0.3f} s")

            sorted_laps = sorted(laps)
            lines = []
            for i, t in enumerate(sorted_laps, start=1):
                lines.append(f"{i:2d}. {t:0.3f} s")
            self.label_lap_list.config(text="\n".join(lines))
        else:
            self.label_last.config(text="Last lap: ---.--- s")
            self.label_best.config(text="Best lap: ---.--- s")
            self.label_lap_list.config(text="No laps yet")

    def exit_fullscreen(self, event=None):
        self.root.destroy()

if __name__ == "__main__":
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

    root = tk.Tk()
    app = RaceApp(root)
    root.mainloop()
