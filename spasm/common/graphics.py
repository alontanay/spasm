import tkinter as tk
from tkinter import ttk
from threading import Lock, Event
import datetime
from queue import Queue, Empty

class ConsoleOutputWidget(tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(font='TkFixedFont',takefocus=0)
        self.yview(tk.END)
        self.lock = Lock()
        self.lines = []
    
    def add_line(self, line):
        self.lines.append(line)
        self.configure(state='normal')
        self.insert(tk.END, f'{str(datetime.datetime.now())[:-7]} > {line}\n')
        self.configure(state='disabled')
        self.yview(tk.END)
        
    def add_text(self, text : str):
        # for line in text.splitlines():
        #     self.add_line(line)
        self.add_line(text)

class LoggerGraphicInterface:
    def handle_updates(self):
        if self.stop_event.is_set():
            self.window.destroy()
            return
        try:
            message = self.logger.get_nowait()
            self.console_output.add_text(message)
            print(message)
        except Empty:
            pass
        self.window.after(100, self.handle_updates)
    
    def __init__(self, logger : Queue, title, subtitle : str, public_key):
        self.logger = logger
        
        self.logger.put('[INTERFACE] Started graphics interface.')
        self.window = tk.Tk()
        style = ttk.Style()
        style.theme_use('classic')
        self.window.geometry('600x500')
        self.window.title(f'{title} - Admin')
        self.name = ttk.Label(text=subtitle,font=('TkDefaultFont',20), background='#EEE')
        self.public_key = ttk.Label(text=f'Public Key: "{public_key}"',font=('Verdana'), background='#EEE')
        self.console_output = ConsoleOutputWidget()
        self.name.pack()
        self.public_key.pack()
        self.console_output.pack(padx=5,pady=5,expand=True, fill='both')
        
        self.window.bind('<Button-1>',lambda event: event.widget == self.window and self.window.focus())
    
    def run(self, stop_event : Event):
        try:
            self.stop_event = stop_event
            self.window.after(100, self.handle_updates)
            self.window.mainloop()
            print('Window Closed.')
            self.stop_event.set()
        except KeyboardInterrupt:
            self.window.destroy()
            self.stop_event.set()
        
