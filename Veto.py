#!/usr/bin/env python3
"""
Veto - A modern autoclicker with dark theme GUI
Author: MyLuxy
"""
import customtkinter as ctk
from PIL import Image, ImageSequence # Manteniamo ImageSequence per non avere dipendenze inter-file
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

# Funzione per gestire i percorsi dei file (per PyInstaller)
def resource_path(relative_path):
    """ Ottiene il percorso assoluto delle risorse, funziona per dev e per PyInstaller """
    try:
        # Quando compilato con PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # Quando eseguito normalmente
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


class HoldMacro:
    """Rappresenta una macro per tenere premuto il tasto (singolo colpo o break continuo)"""
    def __init__(self):
        self.enabled = False
        self.armed = False
        self.active = False
        self.hotkey = None
        self.hotkey_str = "None"
        self.hotkey_is_mouse = False
        self.mode = "single"  # "single" o "break"
        self.cps = 5


class VetoClicker(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- LOGICA ICONA E TASKBAR ---
        icon_name = "assets/veto_icon.ico" 
        full_icon_path = resource_path(icon_name)

        if sys.platform == "win32":
            # Imposta l'ID per la barra delle applicazioni (Windows)
            myappid = 'veto.autoclicker.v1' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            
            # Carica l'icona nella finestra
            try:
                if os.path.exists(full_icon_path):
                    self.iconbitmap(full_icon_path)
            except Exception as e:
                # Può fallire se il file non è disponibile immediatamente (es. durante l'avvio)
                print(f"Errore caricamento icona: {e}")
        # ------------------------------
    

        # Window setup
        self.title("Veto")
        #self.geometry("440x620")
        self.resizable(False, False)
        self.configure(fg_color="#0d0d0d")
        self.center_window(440, 680)
        
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
        
        # Hold Macro
        self.hold_macro = HoldMacro()
        self.hold_macro.enabled = False
        
        # CPS settings (shared)
        self.min_cps = 10
        self.max_cps = 15
        self.randomize = True
        
        # Listeners
        self.keyboard_listener = None
        self.mouse_listener = None
        self.listening_for_hotkey = None
        self.hotkey_cooldown = False
        
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
        
        # Hold Macro
        self.create_hold_section()
        
    
    def create_header(self):
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Caricamento dell'immagine dell'icona (per il logo UI)
        try:
            icon_path = resource_path("assets/VetoComplete.png")
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(icon_path),
                dark_image=Image.open(icon_path),
                size=(140, 56)
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
            text=" Autoclicker",
            font=ctk.CTkFont(family="Segoe UI", size=15, slant="italic"),
            text_color="#383838"
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
        title_color = "#e4e4e7" 
        ctk.CTkLabel(
            header_frame,
            text=f"{macro.name} Click",
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
    
    def create_hold_section(self):
        """Crea la sezione Hold Macro"""
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
        
        ctk.CTkLabel(
            header_frame,
            text="Hold Click",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e4e4e7"
        ).pack(side="left")
        
        self.hold_macro.enabled_var = ctk.BooleanVar(value=False)
        enable_cb = ctk.CTkCheckBox(
            header_frame, text="Enable", variable=self.hold_macro.enabled_var,
            font=ctk.CTkFont(size=11), text_color="#a1a1aa",
            fg_color="#8b5cf6", hover_color="#7c3aed", border_color="#2d2d44",
            command=self.toggle_hold_enabled
        )
        enable_cb.pack(side="right")
        
        # Content
        content = ctk.CTkFrame(inner, fg_color="transparent")
        self.hold_macro.content_widgets = content
        content.pack_forget()  # Nascosto di default
        
        # Hotkey row
        hotkey_frame = ctk.CTkFrame(content, fg_color="transparent")
        hotkey_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            hotkey_frame, text="Hotkey:", font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        ).pack(side="left")
        
        hotkey_btn = ctk.CTkButton(
            hotkey_frame, text=self.hold_macro.hotkey_str, width=100, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1a1a2e", hover_color="#2d2d44",
            border_color="#8b5cf6", border_width=2, text_color="#8b5cf6",
            command=self.start_hold_hotkey_listen
        )
        hotkey_btn.pack(side="left", padx=(10, 0))
        self.hold_macro.hotkey_button = hotkey_btn
        
        # Status indicator
        status_label = ctk.CTkLabel(
            hotkey_frame, text="● OFF", font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ef4444"
        )
        status_label.pack(side="right")
        self.hold_macro.status_label = status_label
        
        # Mode selection
        mode_frame = ctk.CTkFrame(content, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(8, 2))
        
        ctk.CTkLabel(
            mode_frame, text="Mode:", font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        ).pack(side="left")
        
        self.hold_macro.mode_var = ctk.StringVar(value="single")
        mode_menu = ctk.CTkSegmentedButton(
            mode_frame,
            values=["Single Click", "Break"],
            variable=self.hold_macro.mode_var,
            command=self.on_hold_mode_change,
            fg_color="#1a1a2e",
            selected_color="#8b5cf6",
            selected_hover_color="#7c3aed",
            unselected_color="#1a1a2e",
            unselected_hover_color="#2d2d44",
            text_color="#a1a1aa",
            font=ctk.CTkFont(size=11)
        )
        mode_menu.pack(side="left", padx=(10, 0), fill="x", expand=True)
        
        # CPS for single mode
        cps_frame = ctk.CTkFrame(content, fg_color="transparent")
        cps_frame.pack(fill="x", pady=3)
        self.hold_macro.cps_frame = cps_frame
        
        ctk.CTkLabel(
            cps_frame, text="CPS:", font=ctk.CTkFont(size=12),
            text_color="#a1a1aa", width=40, anchor="w"
        ).pack(side="left")
        
        self.hold_macro.cps_var = ctk.StringVar(value="5")
        self.hold_macro.cps_entry = ctk.CTkEntry(
            cps_frame, textvariable=self.hold_macro.cps_var, width=50, height=28,
            fg_color="#1a1a2e", border_color="#2d2d44", text_color="#ffffff"
        )
        self.hold_macro.cps_entry.pack(side="left", padx=(0, 10))
        
        self.hold_macro.cps_slider = ctk.CTkSlider(
            cps_frame, from_=1, to=5, number_of_steps=4,
            command=self.on_hold_cps_slider, height=16,
            fg_color="#1a1a2e", progress_color="#8b5cf6",
            button_color="#a78bfa", button_hover_color="#c4b5fd"
        )
        self.hold_macro.cps_slider.set(5)
        self.hold_macro.cps_slider.pack(side="left", fill="x", expand=True)
        
        # Hint
        ctk.CTkLabel(
            content, text="Single Click: clicks at set CPS (max 5) | Break: holds left button to break blocks",
            font=ctk.CTkFont(size=10), text_color="#52525b"
        ).pack(anchor="w", pady=(4, 0))
    
    def toggle_hold_enabled(self):
        """Attiva/Disattiva lo stato abilitato della hold macro"""
        self.hold_macro.enabled = self.hold_macro.enabled_var.get()
        if self.hold_macro.enabled:
            self.hold_macro.content_widgets.pack(fill="x")
        else:
            self.hold_macro.content_widgets.pack_forget()
            self.hold_macro.armed = False
            self.hold_macro.active = False
            self.update_hold_status()
    
    def start_hold_hotkey_listen(self):
        """Inizia l'ascolto per l'hotkey della hold macro"""
        self.listening_for_hotkey = "hold"
        self.hold_macro.hotkey_button.configure(text="Press...", text_color="#fbbf24")
    
    def on_hold_mode_change(self, value):
        """Gestisce il cambio di modalità della hold macro"""
        if value == "Single Click":
            self.hold_macro.mode = "single"
            self.hold_macro.cps_frame.pack(fill="x", pady=3)
        else:
            self.hold_macro.mode = "break"
            self.hold_macro.cps_frame.pack_forget()
    
    def on_hold_cps_slider(self, value):
        val = int(value)
        self.hold_macro.cps_var.set(str(val))
        self.hold_macro.cps = val
    
    def update_hold_status(self, status=None):
        if status is None:
            if self.hold_macro.active:
                status = "ACTIVE"
            elif self.hold_macro.armed:
                status = "ARMED"
            else:
                status = "OFF"
        
        colors = {
            "OFF": "#ef4444",
            "ARMED": "#fbbf24",
            "ACTIVE": "#22c55e"
        }
        self.hold_macro.status_label.configure(text=f"● {status}", text_color=colors.get(status, "#ef4444"))
    
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
                if self.listening_for_hotkey == "hold":
                    self.hold_macro.hotkey = key
                    self.hold_macro.hotkey_is_mouse = False
                    try:
                        self.hold_macro.hotkey_str = key.char.upper()
                    except AttributeError:
                        self.hold_macro.hotkey_str = str(key).replace("Key.", "").upper()
                    
                    self.after(0, self.update_hold_hotkey_display)
                    self.listening_for_hotkey = None
                    return
                else:
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
            
            # Controlla hold macro hotkey
            if self.hold_macro.enabled and not self.hold_macro.hotkey_is_mouse and self.hold_macro.hotkey == key:
                self.after(0, self.toggle_hold_armed)
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
                if self.listening_for_hotkey == "hold":
                    self.hold_macro.hotkey = button
                    self.hold_macro.hotkey_is_mouse = True
                    self.hold_macro.hotkey_str = self.get_mouse_button_name(button)
                    
                    self.after(0, self.update_hold_hotkey_display)
                    self.listening_for_hotkey = None
                    return
                else:
                    macro = self.listening_for_hotkey
                    macro.hotkey = button
                    macro.hotkey_is_mouse = True
                    macro.hotkey_str = self.get_mouse_button_name(button)
                    
                    self.after(0, lambda: self.update_hotkey_display(macro))
                    self.listening_for_hotkey = None
                    return
            
            # Controlla hold macro hotkey (Mouse 4/5)
            if self.hold_macro.enabled and self.hold_macro.hotkey_is_mouse and self.hold_macro.hotkey == button and pressed:
                self.after(0, self.toggle_hold_armed)
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
    
    def update_hold_hotkey_display(self):
        self.hold_macro.hotkey_button.configure(text=self.hold_macro.hotkey_str, text_color="#8b5cf6")
    
    def toggle_hold_armed(self):
        """Attiva/Disattiva lo stato 'armed' per la hold macro, con cooldown."""
        if self.hotkey_cooldown:
            return
        
        self.hotkey_cooldown = True
        self.after(200, lambda: setattr(self, 'hotkey_cooldown', False))
        
        self.hold_macro.armed = not self.hold_macro.armed
        
        if self.hold_macro.armed:
            self.update_hold_status("ARMED")
            # Avvia l'azione della hold macro
            self.start_hold_action()
        else:
            # Ferma l'azione
            self.hold_macro.active = False
            self.stop_hold_action()
            self.update_hold_status("OFF")
    
    def start_hold_action(self):
        """Avvia l'azione della hold macro"""
        if self.hold_macro.active:
            return
        
        self.hold_macro.active = True
        self.update_hold_status("ACTIVE")
        
        if self.hold_macro.mode == "single":
            # Modalità single click con CPS (max 5)
            thread = threading.Thread(target=self.hold_single_loop, daemon=True)
            thread.start()
        else:
            # Modalità break (tiene premuto il tasto sinistro)
            thread = threading.Thread(target=self.hold_break_loop, daemon=True)
            thread.start()
    
    def stop_hold_action(self):
        """Ferma l'azione della hold macro"""
        if self.hold_macro.armed:
            self.update_hold_status("ARMED")
        else:
            self.update_hold_status("OFF")
    
    def hold_single_loop(self):
        """Loop per la modalità single click (max 5 CPS)"""
        while self.hold_macro.active and self.hold_macro.armed:
            try:
                cps = int(self.hold_macro.cps_var.get())
                # Limita a massimo 5 CPS
                if cps > 5:
                    cps = 5
            except ValueError:
                cps = 5
            
            delay = 1.0 / cps
            
            # Click
            self.ignore_clicks = True
            self.mouse_controller.click(Button.left)
            self.ignore_clicks = False
            
            time.sleep(delay)
        
        self.hold_macro.active = False
        self.after(0, self.stop_hold_action)
    
    def hold_break_loop(self):
        """Loop per la modalità break (tiene premuto il tasto sinistro come quando si rompe un blocco)"""
        # Preme e tiene premuto il pulsante sinistro
        self.ignore_clicks = True
        self.mouse_controller.press(Button.left)
        self.ignore_clicks = False
        
        # Attende finché la macro è attiva e armed
        while self.hold_macro.active and self.hold_macro.armed:
            time.sleep(0.1)
        
        # Rilascia il pulsante quando si disattiva
        self.ignore_clicks = True
        self.mouse_controller.release(Button.left)
        self.ignore_clicks = False
        
        self.hold_macro.active = False
        self.after(0, self.stop_hold_action)
    
    def toggle_armed(self, macro):
        """Attiva/Disattiva lo stato 'armed' per una macro, con cooldown."""
        
        # Implementa il cooldown per prevenire il doppio toggle rapido
        if self.hotkey_cooldown:
            return # Blocca l'esecuzione se è in cooldown
        
        self.hotkey_cooldown = True
        # Rimuovi il cooldown dopo 200ms 
        self.after(200, lambda: setattr(self, 'hotkey_cooldown', False))
        
        # Logica di toggle standard
        macro.armed = not macro.armed
        if macro.armed:
            self.update_macro_status(macro, "ARMED")
        else:
            # Assicurati che il clicking si fermi se disarmi
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
            "hold_enabled": self.hold_macro.enabled,
            "hold_hotkey_str": self.hold_macro.hotkey_str,
            "hold_hotkey_is_mouse": self.hold_macro.hotkey_is_mouse,
            "hold_mode": self.hold_macro.mode,
            "hold_cps": self.hold_macro.cps_var.get(),
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
            
            # Hold macro - PRIMA imposta tutte le variabili
            self.hold_macro.hotkey_str = settings.get("hold_hotkey_str", "None")
            self.hold_macro.hotkey_is_mouse = settings.get("hold_hotkey_is_mouse", False)
            self.hold_macro.mode = settings.get("hold_mode", "single")
            
            hold_cps = settings.get("hold_cps", "5")
            # Assicurati che il CPS non superi 5
            try:
                cps_val = int(hold_cps)
                if cps_val > 5:
                    cps_val = 5
                hold_cps = str(cps_val)
            except:
                hold_cps = "5"
            self.hold_macro.cps_var.set(hold_cps)
            self.hold_macro.cps_slider.set(int(hold_cps))
            
            # POI ripristina l'hotkey
            self.restore_hold_hotkey()
            
            # POI configura il bottone e l'interfaccia
            self.hold_macro.hotkey_button.configure(text=self.hold_macro.hotkey_str)
            self.hold_macro.mode_var.set("Single Click" if self.hold_macro.mode == "single" else "Break")
            self.on_hold_mode_change("Single Click" if self.hold_macro.mode == "single" else "Break")
            
            # INFINE abilita la macro se era abilitata
            if settings.get("hold_enabled", False):
                self.hold_macro.enabled_var.set(True)
                self.toggle_hold_enabled()
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
    
    def restore_hold_hotkey(self):
        if self.hold_macro.hotkey_is_mouse:
            buttons = {"Mouse 4": Button.x1, "Mouse 5": Button.x2}
            self.hold_macro.hotkey = buttons.get(self.hold_macro.hotkey_str)
        else:
            if len(self.hold_macro.hotkey_str) == 1:
                try:
                    self.hold_macro.hotkey = Key.from_char(self.hold_macro.hotkey_str.lower())
                except:
                    pass
            else:
                try:
                    self.hold_macro.hotkey = getattr(Key, self.hold_macro.hotkey_str.lower())
                except:
                    pass
    
    def on_close(self):
        self.save_settings()
        # Blocca i thread di click
        for macro in [self.left_macro, self.right_macro]:
            macro.clicking = False
            macro.armed = False
        self.hold_macro.active = False
        self.hold_macro.armed = False
        # Ferma i listener di input
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.destroy()


if __name__ == "__main__":
    app = VetoClicker()
    app.mainloop()