import customtkinter as ctk
from PIL import Image, ImageSequence
import threading
import time
import os
import sys

# Importa l'applicazione e la funzione helper dal file veto.py
from Veto import VetoClicker, resource_path 

# --- CONFIGURAZIONE SPLASH SCREEN ---
GIF_FILE = "veto_splash.gif"
SPLASH_DURATION_SECONDS = 3.0 # Durata dello splash screen in secondi
SPLASH_WIDTH = 350
SPLASH_HEIGHT = 350
# ------------------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class SplashScreen(ctk.CTk):
    """
    Finestra di caricamento che riproduce una GIF animata.
    """
    def __init__(self):
        super().__init__()
        
        self.after_id = None
        self.frame_index = 0
        
        # --- Configurazione Finestra Splash ---
        self.geometry(f"{SPLASH_WIDTH}x{SPLASH_HEIGHT}")
        self.overrideredirect(True) # Rimuove bordi e barra del titolo
        self.configure(fg_color="#000000") # Sfondo scuro
        self.title("Caricamento Veto...") 
        
        # Centra la finestra sullo schermo
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (SPLASH_WIDTH / 2))
        y = int((screen_height / 2) - (SPLASH_HEIGHT / 2))
        self.geometry(f'+{x}+{y}')
        
        # --- Caricamento GIF e frames ---
        self.tk_frames = []
        try:
            gif_path = resource_path(GIF_FILE)
            self.gif = Image.open(gif_path)
            self.frames = [frame.copy().convert("RGBA") for frame in ImageSequence.Iterator(self.gif)]
            self.frame_delay = self.gif.info.get('duration', 100)
            
            # Pre-carica tutti i CTkImage per una riproduzione fluida
            for frame in self.frames:
                self.tk_frames.append(ctk.CTkImage(light_image=frame, dark_image=frame, size=frame.size))
            
        except Exception as e:
            # Fallback in caso di errore di caricamento
            print(f"Errore caricamento GIF ({GIF_FILE}): {e}. Utilizzo fallback.")
            static_image = Image.new('RGB', (SPLASH_WIDTH, SPLASH_HEIGHT), color='#000000')
            self.tk_frames.append(ctk.CTkImage(light_image=static_image, dark_image=static_image, size=static_image.size))
            self.frame_delay = 1000 
        
        # --- Interfaccia Splash ---
        self.image_label = ctk.CTkLabel(self, text="", image=self.tk_frames[0])
        self.image_label.pack(fill="both", expand=True)

        # Inizia il processo: animazione e timer di chiusura
        self.animate_gif()
        self.after(int(SPLASH_DURATION_SECONDS * 1000), self.close_splash)


    def animate_gif(self):
        """Passa al frame successivo della GIF e si riprogramma"""
        if not self.tk_frames:
            return

        self.frame_index = (self.frame_index + 1) % len(self.tk_frames)
        new_image = self.tk_frames[self.frame_index]
        self.image_label.configure(image=new_image)
        
        # Programma il prossimo frame
        self.after_id = self.after(self.frame_delay, self.animate_gif)


    def close_splash(self):
        """Chiude lo splash screen e lancia l'app principale"""
        if self.after_id:
            self.after_cancel(self.after_id) # Ferma il loop di animazione
        self.destroy()
        
        # Avvia l'app principale
        launch_main_app()


def launch_main_app():
    """Lancia l'applicazione VetoClicker"""
    app = VetoClicker()
    app.mainloop()


if __name__ == "__main__":
    # Avvia la sequenza: Splash Screen -> Main App
    splash = SplashScreen()
    splash.mainloop()