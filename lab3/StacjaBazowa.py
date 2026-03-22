import tkinter as tk
from tkinter import messagebox
import math
import time
from collections import deque
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure



class LCG:
    def __init__(self, seed=1):
        self.a = 16807
        self.c = 2147483647
        self.x = seed if seed > 0 else 1

    def gen(self):
        self.x = (self.a * self.x) % self.c
        return self.x / self.c


class RandomGenerators:
    def __init__(self, seed=None):
        if seed is None:
            seed = int(time.time() * 1000) % 2147483647
        self.rng = LCG(seed)

    def uniform(self):
        return self.rng.gen()

    def poisson(self, lam):
        if lam <= 0:
            return 0

        L = math.exp(-lam)
        k = 0
        p = 1.0

        while p > L:
            k += 1
            p *= self.uniform()

        return k - 1

    def gaussian_truncated_int(self, mean, sigma, min_val, max_val):
        if sigma <= 0:
            return int(round(max(min_val, min(max_val, mean))))

        while True:
            u1 = self.uniform()
            u2 = self.uniform()


            z = math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2)
            value = mean + sigma * z

            if min_val <= value <= max_val:
                return int(round(value))


class Simulator:
    def __init__(self, channels_count, queue_size, lam, mean, sigma, min_t, max_t, sim_time, seed=None):
        self.S = channels_count
        self.queue_size = queue_size
        self.lam = lam
        self.mean = mean
        self.sigma = sigma
        self.min_t = min_t
        self.max_t = max_t
        self.sim_time = sim_time

        self.gen = RandomGenerators(seed)

        self.channels = [None] * self.S
        self.queue = deque()

        self.time = 0
        self.served = 0
        self.rejected = 0

        self.total_arrivals = 0
        self.service_samples_sum = 0.0
        self.service_samples_count = 0

        self.wait_sum = 0.0
        self.wait_count = 0

        self.queue_sum = 0.0

        self.ro_hist = []
        self.Q_hist = []
        self.W_hist = []
        self.time_hist = []

    def _assign_to_free_channel(self, client_duration):
        for i in range(self.S):
            if self.channels[i] is None:
                self.channels[i] = {"remaining": client_duration, "arrival": self.time}
                return True
        return False

    def step(self):
        self.time += 1

        for i in range(self.S):
            if self.channels[i] is not None:
                self.channels[i]["remaining"] -= 1

                if self.channels[i]["remaining"] <= 0:
                    self.served += 1

                    if self.queue:
                        next_client = self.queue.popleft()
                        wait_time = self.time - next_client["arrival"]
                        self.wait_sum += wait_time
                        self.wait_count += 1
                        self.channels[i] = next_client
                    else:
                        self.channels[i] = None

        arrivals = self.gen.poisson(self.lam)
        self.total_arrivals += arrivals

        for _ in range(arrivals):
            duration = self.gen.gaussian_truncated_int(self.mean, self.sigma, self.min_t, self.max_t)
            self.service_samples_sum += duration
            self.service_samples_count += 1

            if self._assign_to_free_channel(duration):

                self.wait_sum += 0
                self.wait_count += 1
            elif len(self.queue) < self.queue_size:
                self.queue.append({
                    "remaining": duration,
                    "arrival": self.time
                })
            else:
                self.rejected += 1


        queue_now = len(self.queue)
        self.queue_sum += queue_now

        Q_avg = self.queue_sum / self.time

        if self.wait_count > 0:
            W_avg = self.wait_sum / self.wait_count
        else:
            W_avg = 0.0

        if self.time > 0:
            lambda_est = self.total_arrivals / self.time
        else:
            lambda_est = 0.0

        if self.service_samples_count > 0:
            mean_service_est = self.service_samples_sum / self.service_samples_count
        else:
            mean_service_est = self.mean


        ro = (lambda_est * mean_service_est) / self.S if self.S > 0 else 0.0

        self.time_hist.append(self.time)
        self.Q_hist.append(Q_avg)
        self.W_hist.append(W_avg)
        self.ro_hist.append(ro)

        return ro, Q_avg, W_avg

    def get_channel_texts(self):
        texts = []
        for ch in self.channels:
            if ch is None:
                texts.append("")
            else:
                texts.append(str(max(0, int(ch["remaining"]))))
        return texts

    def get_channel_states(self):
        return [ch is not None for ch in self.channels]



class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Symulator Stacji Bazowej")

        self.running = False
        self.sim = None

        self.build_ui()

    def build_ui(self):
        top = tk.Frame(self.root)
        top.pack(padx=10, pady=10)

        labels = [
            "Liczba kanalow",
            "Dlugosc kolejki",
            "Lambda",
            "Srednia dlugosc rozmowy",
            "Odchylenie standardowe",
            "Minimalny czas polaczenia",
            "Maksymalny czas polaczenia",
            "Czas symulacji"
        ]
        defaults = ["10", "10", "1", "20", "5", "10", "30", "30"]

        self.entries = []

        for r, (label, default) in enumerate(zip(labels, defaults)):
            tk.Label(top, text=label, anchor="e", width=28).grid(row=r, column=0, sticky="e", padx=4, pady=2)
            entry = tk.Entry(top, width=14)
            entry.insert(0, default)
            entry.grid(row=r, column=1, sticky="w", padx=4, pady=2)
            self.entries.append(entry)

        self.start_button = tk.Button(top, text="START", width=10, command=self.start_simulation)
        self.start_button.grid(row=len(labels), column=0, columnspan=2, pady=(8, 0))


        self.channel_frame = tk.Frame(self.root)
        self.channel_frame.pack(pady=(8, 4))

        self.channel_labels = []


        self.info_label = tk.Label(self.root, text="Czas: 0 | Obsluzone: 0 | Odrzucone: 0 | Q=0.00 | W=0.00 | ro=0.00")
        self.info_label.pack(pady=(2, 6))


        self.fig = Figure(figsize=(7, 7))
        self.ax_Q = self.fig.add_subplot(311)
        self.ax_W = self.fig.add_subplot(312)
        self.ax_ro = self.fig.add_subplot(313)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.ax_Q.set_title("Q")
        self.ax_W.set_title("W")
        self.ax_ro.set_title("ro")

        self.ax_Q.grid(True)
        self.ax_W.grid(True)
        self.ax_ro.grid(True)

    def start_simulation(self):
        if self.running:
            return

        try:
            channels_count = int(self.entries[0].get())
            queue_size = int(self.entries[1].get())
            lam = float(self.entries[2].get())
            mean = float(self.entries[3].get())
            sigma = float(self.entries[4].get())
            min_t = int(self.entries[5].get())
            max_t = int(self.entries[6].get())
            sim_time = int(self.entries[7].get())

            if channels_count <= 0:
                raise ValueError("Liczba kanalow musi byc dodatnia.")
            if queue_size < 0:
                raise ValueError("Dlugosc kolejki nie moze byc ujemna.")
            if lam < 0 or mean <= 0 or sigma < 0 or min_t <= 0 or max_t <= 0 or sim_time <= 0:
                raise ValueError("Parametry musza byc dodatnie.")
            if min_t > max_t:
                raise ValueError("Minimalny czas polaczenia nie moze byc wiekszy od maksymalnego.")

        except ValueError as e:
            messagebox.showerror("Blad danych", str(e))
            return

        self.sim = Simulator(
            channels_count=channels_count,
            queue_size=queue_size,
            lam=lam,
            mean=mean,
            sigma=sigma,
            min_t=min_t,
            max_t=max_t,
            sim_time=sim_time
        )

        self.running = True
        self.start_button.config(state="disabled")
        self.step_loop()

    def step_loop(self):
        if self.sim.time >= self.sim.sim_time:
            self.running = False
            self.start_button.config(state="normal")
            self.save_to_file()
            return

        ro, Q, W = self.sim.step()
        self.draw_channels()

        self.info_label.config(
            text=(
                f"Czas: {self.sim.time} | Obsluzone: {self.sim.served} | "
                f"Odrzucone: {self.sim.rejected} | Q={Q:.2f} | W={W:.2f} | ro={ro:.2f}"
            )
        )

        self.update_plots()
        self.root.after(1000, self.step_loop)

    def draw_channels(self):
        for widget in self.channel_frame.winfo_children():
            widget.destroy()

        texts = self.sim.get_channel_texts()
        states = self.sim.get_channel_states()

        columns = 5
        for i, (txt, busy) in enumerate(zip(texts, states)):
            color = "red" if busy else "green"
            lbl = tk.Label(
                self.channel_frame,
                text=txt,
                width=6,
                height=2,
                bg=color,
                fg="black",
                relief="solid",
                borderwidth=1
            )
            lbl.grid(row=i // columns, column=i % columns, padx=2, pady=2)

    def update_plots(self):
        t = self.sim.time_hist

        self.ax_Q.clear()
        self.ax_W.clear()
        self.ax_ro.clear()

        self.ax_Q.plot(t, self.sim.Q_hist, color="red")
        self.ax_W.plot(t, self.sim.W_hist, color="blue")
        self.ax_ro.plot(t, self.sim.ro_hist, color="green")

        self.ax_Q.set_title("Q")
        self.ax_W.set_title("W")
        self.ax_ro.set_title("ro")

        self.ax_Q.grid(True)
        self.ax_W.grid(True)
        self.ax_ro.grid(True)

        self.canvas.draw_idle()

    def save_to_file(self):
        def fmt(x):
            if abs(x - round(x)) < 1e-10:
                return str(int(round(x)))
            s = f"{x:.4f}".rstrip("0").rstrip(".")
            return s.replace(".", ",")

        with open("wyniki.txt", "w", encoding="utf-8") as f:
            f.write("Parametry symulacji:\n\n")
            f.write(f"Liczba kanalow: {self.sim.S}\n")
            f.write(f"Dlugosc kolejki: {self.sim.queue_size}\n")
            f.write(f"Lambda: {self.sim.lam}\n")
            f.write(f"Srednia dlugosc rozmowy: {self.sim.mean}\n")
            f.write(f"Odchylenie: {self.sim.sigma}\n")
            f.write(f"Minimalny czas polaczenia: {self.sim.min_t}\n")
            f.write(f"Maksymalny czas polaczenia: {self.sim.max_t}\n")
            f.write(f"Czas symulacji: {self.sim.sim_time}\n\n")

            f.write("Ro\t\tQ\t\tW\n")
            for ro, q, w in zip(self.sim.ro_hist, self.sim.Q_hist, self.sim.W_hist):
                f.write(f"{fmt(ro)}\t\t{fmt(q)}\t\t{fmt(w)}\n")

        messagebox.showinfo("Zapisano", "Wyniki zostaly zapisane do pliku wyniki.txt")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()