#!/usr/bin/env python3
"""
Veto - A modern autoclicker with dark theme GUI
Author: MyLuxy
"""
import customtkinter as ctk
from PIL import Image, ImageSequence
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController, Listener as MouseListener
from pynput.keyboard import Key, Listener as KeyboardListener
import threading
import time
import random
import json
import os
import sys
import ctypes

# Theme configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Funzione per gestire i percorsi dei file /pynstaller
def resource_path(relative_path):
    """ Ottiene il percorso assoluto delle risorse, funziona per dev e per PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ClickMacro:
    """Rappresenta una singola macro di click (sinistro o destro)"""
    def __init__(self, name, button):
        self.name = name  # "Left" or "Right"
        self.button = button  # Button.left or Button.right
        self.enabled = False
        self.armed = False
        self.clicking = False
        self.hotkey = None
        self.hotkey_str = "None"
        self.hotkey_is_mouse = False
        self.min_cps = 10
        self.max_cps = 15
        self.mouse_held = False


class VetoClicker(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        icon_name = "veto_icon.ico" 
        full_icon_path = resource_path(icon_name)

        if sys.platform == "win32":
            myappid = 'veto.autoclicker.v1' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            
            try:
                if os.path.exists(full_icon_path):
                    self.iconbitmap(full_icon_path)
            except Exception as e:
                print(f"Errore caricamento icona: {e}")
    
        self.title("Veto")
        #self.geometry("440x620")
        self.resizable(False, False)
        self.configure(fg_color="#0d0d0d")
        self.center_window(440, 620)
        
        # Mouse controller
        self.mouse_controller = MouseController()
        self.ignore_clicks = False
        
        # Macros
        self.left_macro = ClickMacro("Left", Button.left)
        self.left_macro.enabled = True  # Left è abilitato di default
        self.left_macro.hotkey = Key.f6
        self.left_macro.hotkey_str = "F6"
        
        self.right_macro = ClickMacro("Right", Button.right)
        self.right_macro.enabled = False
        
        # CPS settings (shared)
        self.min_cps = 10
        self.max_cps = 15
        self.randomize = True
        
        # Listeners
        self.keyboard_listener = None
        self.mouse_listener = None
        self.listening_for_hotkey = None  # Quale macro è in ascolto
        
        # Build UI
        self.create_ui()
        
        # Start input listeners
        self.start_input_listeners()
        
        # Load settings
        self.load_settings()
        
        # Protocollo per una chiusura pulita
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def center_window(self, width, height):
        """Calcola la posizione per centrare la finestra sullo schermo."""
        
        # Ottiene la larghezza e l'altezza dello schermo
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calcola le coordinate x e y per centrare
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        
        # Imposta la geometria (dimensione e posizione)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.update_idletasks()

    def create_ui(self):
        # Contenitore principale
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Header
        self.create_header()
        
        # CPS Section (shared)
        self.create_cps_section()
        
        # Left Click Macro
        self.create_macro_section(self.left_macro)
        
        # Right Click Macro (collapsible)
        self.create_macro_section(self.right_macro)
        
        # Status Section
        self.create_status_section()
        
    
    def create_header(self):
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Caricamento dell'immagine dell'icona (per il logo UI)
        try:
            icon_path = resource_path("veto_icon.ico")
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(icon_path),
                dark_image=Image.open(icon_path),
                size=(60, 60)
            )
            
            logo = ctk.CTkLabel(
                header_frame, 
                text="", 
                image=self.logo_image
            )
        except Exception as e:
            print(f"Errore caricamento immagine UI: {e}")
            logo = ctk.CTkLabel(
                header_frame,
                text="V",
                font=ctk.CTkFont(family="Segoe UI", size=42, weight="bold"),
                text_color="#8b5cf6"
            )
            
        logo.pack()
        
        title = ctk.CTkLabel(
            header_frame,
            text="VETO",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#a78bfa"
        )
        title.pack(pady=(0, 0))
    
    def create_cps_section(self):
        section = self.create_section("CPS Settings")
        
        # Min CPS
        min_frame = ctk.CTkFrame(section, fg_color="transparent")
        min_frame.pack(fill="x", pady=3)
        
        ctk.CTkLabel(
            min_frame, text="Min CPS:", font=ctk.CTkFont(size=12),
            text_color="#a1a1aa", width=60, anchor="w"
        ).pack(side="left")
        
        self.min_cps_var = ctk.StringVar(value="10")
        self.min_cps_entry = ctk.CTkEntry(
            min_frame, textvariable=self.min_cps_var, width=50, height=28,
            fg_color="#1a1a2e", border_color="#2d2d44", text_color="#ffffff"
        )
        self.min_cps_entry.pack(side="left", padx=(0, 10))
        
        self.min_slider = ctk.CTkSlider(
            min_frame, from_=1, to=20, number_of_steps=19,
            command=self.on_min_slider, height=16,
            fg_color="#1a1a2e", progress_color="#8b5cf6",
            button_color="#a78bfa", button_hover_color="#c4b5fd"
        )
        self.min_slider.set(10)
        self.min_slider.pack(side="left", fill="x", expand=True)
        
        # Max CPS
        max_frame = ctk.CTkFrame(section, fg_color="transparent")
        max_frame.pack(fill="x", pady=3)
        
        ctk.CTkLabel(
            max_frame, text="Max CPS:", font=ctk.CTkFont(size=12),
            text_color="#a1a1aa", width=60, anchor="w"
        ).pack(side="left")
        
        self.max_cps_var = ctk.StringVar(value="15")
        self.max_cps_entry = ctk.CTkEntry(
            max_frame, textvariable=self.max_cps_var, width=50, height=28,
            fg_color="#1a1a2e", border_color="#2d2d44", text_color="#ffffff"
        )
        self.max_cps_entry.pack(side="left", padx=(0, 10))
        
        self.max_slider = ctk.CTkSlider(
            max_frame, from_=1, to=20, number_of_steps=19,
            command=self.on_max_slider, height=16,
            fg_color="#1a1a2e", progress_color="#8b5cf6",
            button_color="#a78bfa", button_hover_color="#c4b5fd"
        )
        self.max_slider.set(15)
        self.max_slider.pack(side="left", fill="x", expand=True)
        
        # Randomize
        self.randomize_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            section, text="Randomize CPS", variable=self.randomize_var,
            font=ctk.CTkFont(size=11), text_color="#a1a1aa",
            fg_color="#8b5cf6", hover_color="#7c3aed", border_color="#2d2d44"
        ).pack(anchor="w", pady=(5, 0))
    
    def create_macro_section(self, macro):
        """Crea una sezione per una macro di click"""
        
        # Main frame for macro
        frame = ctk.CTkFrame(
            self.main_frame, fg_color="#141420",
            corner_radius=10, border_width=1, border_color="#1e1e2e"
        )
        frame.pack(fill="x", pady=(0, 8))
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(padx=12, pady=10, fill="x")
        
        # Header with enable checkbox
        header_frame = ctk.CTkFrame(inner, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 8))
        
        # Title
        title_color = "#22c55e" if macro.name == "Left" else "#ef4444"
        ctk.CTkLabel(
            header_frame,
            text=f"● {macro.name} Click",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=title_color
        ).pack(side="left")
        
        # Enable checkbox (solo per la macro destra)
        if macro.name == "Right":
            macro.enabled_var = ctk.BooleanVar(value=False)
            enable_cb = ctk.CTkCheckBox(
                header_frame, text="Enable", variable=macro.enabled_var,
                font=ctk.CTkFont(size=11), text_color="#a1a1aa",
                fg_color="#8b5cf6", hover_color="#7c3aed", border_color="#2d2d44",
                command=lambda: self.toggle_macro_enabled(macro)
            )
            enable_cb.pack(side="right")
            macro.content_frame = inner
        
        # Content (hotkey selection)
        content = ctk.CTkFrame(inner, fg_color="transparent")
        content.pack(fill="x")
        
        if macro.name == "Right":
            macro.content_widgets = content
            content.pack_forget()  # Nascosto di default
        
        # Hotkey row
        hotkey_frame = ctk.CTkFrame(content, fg_color="transparent")
        hotkey_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            hotkey_frame, text="Hotkey:", font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        ).pack(side="left")
        
        hotkey_btn = ctk.CTkButton(
            hotkey_frame, text=macro.hotkey_str, width=100, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1a1a2e", hover_color="#2d2d44",
            border_color="#8b5cf6", border_width=2, text_color="#8b5cf6",
            command=lambda m=macro: self.start_hotkey_listen(m)
        )
        hotkey_btn.pack(side="left", padx=(10, 0))
        macro.hotkey_button = hotkey_btn
        
        # Status indicator
        status_label = ctk.CTkLabel(
            hotkey_frame, text="● OFF", font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ef4444"
        )
        status_label.pack(side="right")
        macro.status_label = status_label
        
        # Hint
        ctk.CTkLabel(
            content, text="Click button, then press key or Mouse 4/5",
            font=ctk.CTkFont(size=10), text_color="#52525b"
        ).pack(anchor="w", pady=(4, 0))
    
    def toggle_macro_enabled(self, macro):
        """Attiva/Disattiva lo stato abilitato della macro"""
        macro.enabled = macro.enabled_var.get()
        if macro.enabled:
            macro.content_widgets.pack(fill="x")
        else:
            macro.content_widgets.pack_forget()
            macro.armed = False
            macro.clicking = False
            self.update_macro_status(macro)
    
    def create_status_section(self):
        status_frame = ctk.CTkFrame(
            self.main_frame, fg_color="#1a1a2e",
            corner_radius=12, border_width=1, border_color="#2d2d44"
        )
        status_frame.pack(fill="x", pady=(10, 0))
        
        inner = ctk.CTkFrame(status_frame, fg_color="transparent")
        inner.pack(padx=15, pady=12, fill="x")
        
        # Current CPS
        cps_row = ctk.CTkFrame(inner, fg_color="transparent")
        cps_row.pack(fill="x")
        
        ctk.CTkLabel(
            cps_row, text="Current CPS:",
            font=ctk.CTkFont(size=13), text_color="#a1a1aa"
        ).pack(side="left")
        
        self.current_cps_label = ctk.CTkLabel(
            cps_row, text="0",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#8b5cf6"
        )
        self.current_cps_label.pack(side="left", padx=(10, 0))
        
        # Instructions
        self.instruction_label = ctk.CTkLabel(
            inner, text="Press hotkey to arm, then hold mouse button",
            font=ctk.CTkFont(size=11), text_color="#52525b"
        )
        self.instruction_label.pack(pady=(10, 0))
    
    def create_section(self, title):
        frame = ctk.CTkFrame(
            self.main_frame, fg_color="#141420",
            corner_radius=10, border_width=1, border_color="#1e1e2e"
        )
        frame.pack(fill="x", pady=(0, 8))
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(padx=12, pady=10, fill="x")
        
        ctk.CTkLabel(
            inner, text=title,
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#e4e4e7"
        ).pack(anchor="w", pady=(0, 8))
        
        return inner
    
    def on_min_slider(self, value):
        val = int(value)
        self.min_cps_var.set(str(val))
        self.min_cps = val
        if val > int(self.max_cps_var.get()):
            self.max_slider.set(val)
            self.max_cps_var.set(str(val))
            self.max_cps = val
    
    def on_max_slider(self, value):
        val = int(value)
        self.max_cps_var.set(str(val))
        self.max_cps = val
        if val < int(self.min_cps_var.get()):
            self.min_slider.set(val)
            self.min_cps_var.set(str(val))
            self.min_cps = val
    
    def start_hotkey_listen(self, macro):
        """Inizia l'ascolto per l'hotkey per una macro specifica"""
        self.listening_for_hotkey = macro
        macro.hotkey_button.configure(text="Press...", text_color="#fbbf24")
    
    def get_mouse_button_name(self, button):
        names = {
            Button.left: "Mouse Left",
            Button.right: "Mouse Right",
            Button.middle: "Mouse Middle",
            Button.x1: "Mouse 4",
            Button.x2: "Mouse 5",
        }
        return names.get(button, str(button))
    
    def start_input_listeners(self):
        def on_key_press(key):
            # Modalità di selezione Hotkey
            if self.listening_for_hotkey:
                macro = self.listening_for_hotkey
                macro.hotkey = key
                macro.hotkey_is_mouse = False
                try:
                    # Tasto carattere
                    macro.hotkey_str = key.char.upper()
                except AttributeError:
                    # Tasto speciale (F6, shift, ctrl...)
                    macro.hotkey_str = str(key).replace("Key.", "").upper()
                
                self.after(0, lambda: self.update_hotkey_display(macro))
                self.listening_for_hotkey = None
                return
            
            # Controlla se il tasto corrisponde a un hotkey di macro
            for macro in [self.left_macro, self.right_macro]:
                if macro.enabled and not macro.hotkey_is_mouse and macro.hotkey == key:
                    self.after(0, lambda m=macro: self.toggle_armed(m))
        
        def on_key_release(key):
            pass
        
        def on_mouse_click(x, y, button, pressed):
            if self.ignore_clicks:
                return
            
            # Modalità di selezione Hotkey (Mouse 4/5)
            if self.listening_for_hotkey and pressed and button in [Button.x1, Button.x2]:
                macro = self.listening_for_hotkey
                macro.hotkey = button
                macro.hotkey_is_mouse = True
                macro.hotkey_str = self.get_mouse_button_name(button)
                
                self.after(0, lambda: self.update_hotkey_display(macro))
                self.listening_for_hotkey = None
                return
            
            # Controlla se il pulsante è un hotkey di macro (Mouse 4/5)
            for macro in [self.left_macro, self.right_macro]:
                if macro.enabled and macro.hotkey_is_mouse and macro.hotkey == button and pressed:
                    self.after(0, lambda m=macro: self.toggle_armed(m))
                    return
            
            # Pulsante sinistro controlla la macro sinistra
            if button == Button.left:
                macro = self.left_macro
                if macro.enabled and macro.armed:
                    if pressed:
                        macro.mouse_held = True
                        self.after(0, lambda: self.start_clicking(macro))
                    else:
                        macro.mouse_held = False
                        if macro.clicking:
                            self.after(0, lambda: self.stop_clicking_keep_armed(macro))
            
            # Pulsante destro controlla la macro destra
            elif button == Button.right:
                macro = self.right_macro
                if macro.enabled and macro.armed:
                    if pressed:
                        macro.mouse_held = True
                        self.after(0, lambda: self.start_clicking(macro))
                    else:
                        macro.mouse_held = False
                        if macro.clicking:
                            self.after(0, lambda: self.stop_clicking_keep_armed(macro))
        
        self.keyboard_listener = KeyboardListener(on_press=on_key_press, on_release=on_key_release)
        self.keyboard_listener.start()
        
        self.mouse_listener = MouseListener(on_click=on_mouse_click)
        self.mouse_listener.start()
    
    def update_hotkey_display(self, macro):
        macro.hotkey_button.configure(text=macro.hotkey_str, text_color="#8b5cf6")
    
    def toggle_armed(self, macro):
        """Attiva/Disattiva lo stato 'armed' per una macro"""
        macro.armed = not macro.armed
        if macro.armed:
            self.update_macro_status(macro, "ARMED")
        else:
            macro.clicking = False
            self.update_macro_status(macro, "OFF")
    
    def update_macro_status(self, macro, status=None):
        if status is None:
            if macro.clicking:
                status = "CLICKING"
            elif macro.armed:
                status = "ARMED"
            else:
                status = "OFF"
        
        colors = {
            "OFF": "#ef4444",
            "ARMED": "#fbbf24",
            "CLICKING": "#22c55e"
        }
        macro.status_label.configure(text=f"● {status}", text_color=colors.get(status, "#ef4444"))
    
    def start_clicking(self, macro):
        if macro.clicking:
            return
        
        macro.clicking = True
        self.update_macro_status(macro, "CLICKING")
        
        # Esegue il loop di click in un thread separato
        thread = threading.Thread(target=lambda: self.click_loop(macro), daemon=True)
        thread.start()
    
    def stop_clicking_keep_armed(self, macro):
        macro.clicking = False
        self.current_cps_label.configure(text="0")
        if macro.armed:
            self.update_macro_status(macro, "ARMED")
        else:
            self.update_macro_status(macro, "OFF")
    
    def click_loop(self, macro):
        while macro.clicking and macro.mouse_held:
            try:
                min_cps = int(self.min_cps_var.get())
                max_cps = int(self.max_cps_var.get())
            except ValueError:
                min_cps, max_cps = 10, 15
            
            if self.randomize_var.get():
                cps = random.uniform(min_cps, max_cps)
            else:
                cps = (min_cps + max_cps) / 2
            
            delay = 1.0 / cps
            
            if self.randomize_var.get():
                # Aggiunge una leggera randomizzazione al ritardo
                delay *= random.uniform(0.85, 1.15)
            
            # Click
            self.ignore_clicks = True
            self.mouse_controller.click(macro.button)
            self.ignore_clicks = False
            
            # Update CPS in the GUI
            actual_cps = round(1.0 / delay, 1)
            # Usa self.after per aggiornare la GUI dal thread secondario
            self.after(0, lambda c=actual_cps: self.current_cps_label.configure(text=str(c)))
            
            time.sleep(delay)
        
        macro.clicking = False
        self.after(0, lambda: self.stop_clicking_keep_armed(macro))
    
    def save_settings(self):
        settings = {
            "min_cps": self.min_cps_var.get(),
            "max_cps": self.max_cps_var.get(),
            "randomize": self.randomize_var.get(),
            "left_hotkey_str": self.left_macro.hotkey_str,
            "left_hotkey_is_mouse": self.left_macro.hotkey_is_mouse,
            "right_enabled": self.right_macro.enabled,
            "right_hotkey_str": self.right_macro.hotkey_str,
            "right_hotkey_is_mouse": self.right_macro.hotkey_is_mouse,
        }
        
        config_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json")
        try:
            with open(config_path, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            # Qui non stampa l'errore, ma è più sicuro per un'applicazione compilata
            pass
    
    def load_settings(self):
        # Tenta di caricare da settings.json
        config_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json")
        try:
            with open(config_path, "r") as f:
                settings = json.load(f)
            
            self.min_cps_var.set(settings.get("min_cps", "10"))
            self.max_cps_var.set(settings.get("max_cps", "15"))
            self.min_slider.set(int(settings.get("min_cps", 10)))
            self.max_slider.set(int(settings.get("max_cps", 15)))
            self.randomize_var.set(settings.get("randomize", True))
            
            # Left macro
            self.left_macro.hotkey_str = settings.get("left_hotkey_str", "F6")
            self.left_macro.hotkey_is_mouse = settings.get("left_hotkey_is_mouse", False)
            self.left_macro.hotkey_button.configure(text=self.left_macro.hotkey_str)
            self.restore_hotkey(self.left_macro)
            
            # Right macro
            if settings.get("right_enabled", False):
                self.right_macro.enabled_var.set(True)
                self.toggle_macro_enabled(self.right_macro)
            self.right_macro.hotkey_str = settings.get("right_hotkey_str", "None")
            self.right_macro.hotkey_is_mouse = settings.get("right_hotkey_is_mouse", False)
            self.right_macro.hotkey_button.configure(text=self.right_macro.hotkey_str)
            self.restore_hotkey(self.right_macro)
        except:
            pass
    
    def restore_hotkey(self, macro):
        if macro.hotkey_is_mouse:
            buttons = {"Mouse 4": Button.x1, "Mouse 5": Button.x2}
            macro.hotkey = buttons.get(macro.hotkey_str)
        else:
            if len(macro.hotkey_str) == 1:
                try:
                    # Carattere normale
                    macro.hotkey = Key.from_char(macro.hotkey_str.lower())
                except:
                    # Fallback
                    pass
            else:
                try:
                    # Tasto speciale
                    macro.hotkey = getattr(Key, macro.hotkey_str.lower())
                except:
                    # Fallback, usa F6 se non valido
                    macro.hotkey = Key.f6
    
    def on_close(self):
        self.save_settings()
        # Blocca i thread di click
        for macro in [self.left_macro, self.right_macro]:
            macro.clicking = False
            macro.armed = False
        # Ferma i listener di input
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

        self.destroy()
