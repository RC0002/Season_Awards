# -*- coding: utf-8 -*-
"""
Season Awards Scraper - Desktop App
====================================
GUI app to run the scraper with real-time output.
Uses CustomTkinter for modern dark theme with gold accents.

Requirements:
    pip install customtkinter

Usage:
    python scraper_app.py
"""

import customtkinter as ctk
import subprocess
import threading
import sys
import os
from datetime import datetime

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Colors matching web app
GOLD = "#d4a84b"
GOLD_DARK = "#b8923f"
BG_DARK = "#121212"
CARD_BG = "#1e1e1e"
TEXT = "#ffffff"
MUTED = "#888888"


class ScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Season Awards Scraper")
        self.geometry("800x600")
        self.configure(fg_color=BG_DARK)
        
        # State
        self.process = None
        self.is_running = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=80)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="🎬 SEASON AWARDS SCRAPER",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=GOLD
        )
        title_label.pack(pady=20)
        
        # Main content
        content_frame = ctk.CTkFrame(self, fg_color=BG_DARK)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Button row
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 15))
        
        self.run_button = ctk.CTkButton(
            button_frame,
            text="▶ Avvia Scraping",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=GOLD,
            hover_color=GOLD_DARK,
            text_color="#000000",
            height=45,
            corner_radius=8,
            command=self.run_scraper
        )
        self.run_button.pack(side="left", padx=(0, 10))
        
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⬛ Stop",
            font=ctk.CTkFont(size=14),
            fg_color="#444444",
            hover_color="#555555",
            text_color=TEXT,
            height=45,
            corner_radius=8,
            state="disabled",
            command=self.stop_scraper
        )
        self.stop_button.pack(side="left", padx=(0, 10))
        
        self.clear_button = ctk.CTkButton(
            button_frame,
            text="🗑 Pulisci Log",
            font=ctk.CTkFont(size=14),
            fg_color="#333333",
            hover_color="#444444",
            text_color=TEXT,
            height=45,
            corner_radius=8,
            command=self.clear_log
        )
        self.clear_button.pack(side="left")
        
        # Status
        self.status_label = ctk.CTkLabel(
            button_frame,
            text="● Pronto",
            font=ctk.CTkFont(size=14),
            text_color="#4ade80"  # green
        )
        self.status_label.pack(side="right", padx=10)
        
        # Output text area
        output_label = ctk.CTkLabel(
            content_frame,
            text="OUTPUT",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD
        )
        output_label.pack(anchor="w")
        
        self.output_text = ctk.CTkTextbox(
            content_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=CARD_BG,
            text_color=TEXT,
            corner_radius=8,
            wrap="word"
        )
        self.output_text.pack(fill="both", expand=True, pady=(5, 0))
        
        # Welcome message
        self.log(f"[{self.get_time()}] Season Awards Scraper pronto.\n")
        self.log("Clicca 'Avvia Scraping' per iniziare.\n")
        
    def get_time(self):
        return datetime.now().strftime("%H:%M:%S")
    
    def log(self, text):
        self.output_text.insert("end", text)
        self.output_text.see("end")
        
    def clear_log(self):
        self.output_text.delete("1.0", "end")
        
    def run_scraper(self):
        if self.is_running:
            return
            
        self.is_running = True
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_label.configure(text="● In esecuzione...", text_color=GOLD)
        
        self.log(f"\n[{self.get_time()}] ========== AVVIO SCRAPING ==========\n")
        
        # Run in thread to keep UI responsive
        thread = threading.Thread(target=self.execute_scraper, daemon=True)
        thread.start()
        
    def execute_scraper(self):
        try:
            # Change to project directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            os.chdir(script_dir)
            
            # Run the scraper
            self.process = subprocess.Popen(
                [sys.executable, "scraper/scrape_and_upload.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
            # Read output line by line
            for line in iter(self.process.stdout.readline, ''):
                if not self.is_running:
                    break
                # Update UI from main thread
                self.after(0, lambda l=line: self.log(l))
                
            self.process.wait()
            
            # Done
            self.after(0, self.scraper_finished)
            
        except Exception as e:
            self.after(0, lambda: self.log(f"\n❌ ERRORE: {str(e)}\n"))
            self.after(0, self.scraper_finished)
            
    def scraper_finished(self):
        self.is_running = False
        self.process = None
        self.run_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="● Completato", text_color="#4ade80")
        self.log(f"\n[{self.get_time()}] ========== SCRAPING COMPLETATO ==========\n")
        
    def stop_scraper(self):
        if self.process:
            self.process.terminate()
            self.is_running = False
            self.log(f"\n[{self.get_time()}] ⚠️ Scraping interrotto dall'utente.\n")
            self.status_label.configure(text="● Interrotto", text_color="#f87171")
            self.run_button.configure(state="normal")
            self.stop_button.configure(state="disabled")


if __name__ == "__main__":
    app = ScraperApp()
    app.mainloop()
