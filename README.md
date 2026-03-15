# PyPacker
A lightweight PyQt6 GUI tool built on PyInstaller for one-click packaging Python scripts into standalone executables, optimized for Windows. It features real-time logging, multi-language support, and flexible build configurations with zero command-line operations required.

## 📋 Table of Contents
- [Key Features](#-key-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Advanced Usage](#-advanced-usage)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

## ✨ Key Features
- Intuitive PyQt6 GUI with point-and-click operation
- PyInstaller integration: one-file/one-directory packaging modes
- Console/windowed mode toggle (with secondary confirmation for windowed)
- Custom executable icon (ICO), program name and version info file
- Add external resource files (`--add-data`) and hidden imports (`--hidden-import`)
- Real-time packaging logs and progress bar tracking
- Multi-threaded building (no GUI freezes)
- One-click English/Chinese interface switch
- Persistent configuration (saved to local JSON)
- Built-in PyInstaller check and one-click installation
- Useful shortcuts (Ctrl+O: open file, Ctrl+Q: exit, Ctrl+, : settings)
- One-click output directory access after successful packaging
- Auto-fill program name and display selected file size

## 📌 Prerequisites
- Python 3.8 or higher
- Windows operating system (primary support)
- Default pip package manager

## 🚀 Installation
1. Clone the repository
   ```bash
   git clone https://github.com/Hrecer/PyPacker.git
   cd PyPacker
   ```
2. Install the only dependency
   ```bash
   pip install PyQt6>=6.5.0
   ```
   Or create a `requirements.txt` with `PyQt6>=6.5.0` and run:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Quick Start
1. Launch the tool
   ```bash
   python Python文件编译工具.py
   ```
2. Select your target `.py` script via the **Browse** button
3. Configure basic options:
   - Choose output mode (one-file/one-directory)
   - Toggle console window (uncheck for GUI scripts)
   - Keep default checks for overwriting output and cleaning temp files
4. (Optional) Set custom icon, output directory or version info file
5. Click **Start Packaging** and monitor progress in the right log panel
6. Find the packaged executable in the `dist/` folder (or custom output directory)

## ⚙️ Advanced Usage
### Add Resource Files
- In **Advanced Options**, click **Add File** under *Additional Files*
- Select source files/folders and specify their target path in the executable
- Clear all added files with the **Clear** button

### Add Hidden Imports
- In **Advanced Options**, click **Add Module** under *Hidden Imports*
- Enter the dynamically imported module name (e.g., `requests`, `PIL.Image`)
- Clear all added modules with the **Clear** button

### Custom Settings
- Open settings via **Tools > Settings** or `Ctrl+,`
- Configure Python interpreter path, UPX compression directory, optimization level (0-2)
- Toggle code stripping and UPX compression (UPX requires manual path configuration)
- Save settings (auto-stored to local JSON)

## 🛠️ Configuration
- All settings are saved to `~/.pypacker_settings.json` (Windows: `C:\Users\YourName\.pypacker_settings.json`)
- Core config items: `python_path`, `upx_path`, `work_dir`, `strip`, `upx`, `optimize`
- No manual modification required for normal use

## 🐛 Troubleshooting
1. **PyInstaller Not Found**: Click **Yes** for auto-install, or run `pip install pyinstaller` manually
2. **Missing Module Error**: Add the module to *Hidden Imports* in Advanced Options
3. **Icon Not Working**: Use a valid ICO file (no format conversion) with no Chinese/spaces in the path
4. **Packaging Failure**: Check the real-time log for error details; ensure the Python script runs independently
5. **GUI Freeze**: Restart the tool and check for infinite loops in your Python script

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m "Add: Your feature description"`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

Follow PEP 8 code style and ensure all modifications are tested.

## 📄 License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 📧 Contact
- Project Repository: [https://github.com/Hrecer/PyPacker](https://github.com/Hrecer/PyPacker)
- Issue Submission: [https://github.com/Hrecer/PyPacker/issues](https://github.com/Hrecer/PyPacker/issues)

⭐ Star this repository if PyPacker simplifies your Python packaging workflow!
