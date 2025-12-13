<p align="center">
  <img src="https://github.com/user-attachments/assets/77d806d4-150a-4f3a-af2d-b20ef3d53a18" alt="Anteprima Veto 3D" width="700"/> 
  </p>




### ✨ Key Features

  * **Minimalist Design:** Sleek Dark Theme GUI built using `CustomTkinter` for easy reading and a modern look.
  * **Advanced CPS Control:** Ability to set **Min** and **Max CPS** ranges with a **Randomization** option to simulate more natural, human-like input.
  * **Flexible Hotkeys:** Supports quick arming/disarming using standard keyboard keys (e.g., F6) or dedicated side mouse buttons (Mouse 4 / Mouse 5).
  * **Separate Macros:** Independent control and optional activation for both **Left** and **Right** click macros.
  * **Cross-Platform Ready:** Core logic is designed to be compatible with Windows, macOS, and Linux.
  * **Persistent Settings:** CPS settings and hotkeys are automatically saved for your next session.

-----

## 💦 Preview

<img width="500" height="696" alt="VetoParallax" src="https://github.com/user-attachments/assets/4202a7c5-12e2-4e05-b725-20e6de4d4d97" />&nbsp;&nbsp;


### 🚀 How to Use Veto (Quick Start)

1.  **Set CPS Range:** Adjust the **Min CPS** and **Max CPS** sliders to your desired values.
2.  **Choose Hotkey:** Click the **Hotkey** button and press the key you want to use (e.g., `F6` or `Mouse 4`).
3.  **Arm the Macro:** Press the configured Hotkey. The macro status will change from `● OFF` (red) to `● ARMED` (yellow/orange).
4.  **Start Clicking:** Hold down the corresponding mouse button (Left or Right). The status will change to `● CLICKING` (green).
5.  **Disarm:** Release the mouse button and, when finished, press the Hotkey again to fully disarm the macro (`● OFF`).

-----

### 🛠️ Building from Source

If you wish to compile Veto from the source code, you will need Python 3 and the following dependencies:

#### Python Dependencies

```bash
pip install customtkinter pynput Pillow
```

#### Compiling for Linux (Maximum Compatibility via Docker)

For the best compatibility across various Linux distributions, use a Docker container to compile the executable:

```bash
docker run --rm \
-v "${PWD}:/src" \
pyinstaller/pyinstaller:latest \
pyinstaller --noconfirm --onefile --windowed --name "VetoClicker" \
--add-data "veto_icon.ico:." \
--add-data "veto_splash.gif:." \
--add-data "veto.py:." \
--add-data "settings.json:." \
--hidden-import "pynput.mouse" \
--hidden-import "pynput.keyboard" \
"main_launcher.py"
```

-----

### 📄 License

This project is licensed under the MIT License.

-----

### Contact me

You can contact me on telegram for suggestions, bug reports, and feature contributions. [@MyLuxy](https://t.me/MyLuxy)
