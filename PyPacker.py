#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyPacker - Python File Compilation Tool v1.0
Graphical packaging tool based on PyInstaller
"""

import os
import sys
import subprocess
import threading
import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QCheckBox, QComboBox,
    QFileDialog, QMessageBox, QGroupBox, QGridLayout, QSpinBox,
    QTabWidget, QProgressBar, QSplitter, QListWidget, QListWidgetItem,
    QMenu, QMenuBar, QStatusBar, QToolBar, QDialog, QDialogButtonBox,
    QRadioButton, QButtonGroup, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont, QAction, QTextCursor, QPalette, QColor


class BuildWorker(QThread):
    """Packaging worker thread"""
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(int)
    
    def __init__(self, script_path, options):
        super().__init__()
        self.script_path = script_path
        self.options = options
        self.process = None
        self.is_running = True
        
    def run(self):
        """Execute packaging command"""
        try:
            # Build PyInstaller command
            cmd = self._build_command()
            
            self.output_signal.emit(f"Executing command: {' '.join(cmd)}\n")
            self.output_signal.emit("=" * 60 + "\n")
            
            # 修复：打包成EXE时，subprocess的创建参数调整
            creationflags = 0
            if sys.platform == 'win32':
                # 取消CREATE_NO_WINDOW，临时显示控制台看错误（调试用）
                creationflags = 0  # 原为subprocess.CREATE_NO_WINDOW
            
            # Create process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creationflags,
                # 修复：指定工作目录，避免路径混乱
                cwd=os.path.dirname(self.script_path) if self.script_path else os.getcwd()
            )
            
            # 新增：实时输出每一行，包括错误
            progress_patterns = {
                ' Analyzing ': 10,
                ' Processing ': 30,
                ' Building ': 50,
                ' Building PKG': 60,
                ' Building EXE': 70,
                ' Building COLLECT': 80,
                ' complete.': 100
            }
            
            while True:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    self.output_signal.emit(line.strip())
                    # 进度更新逻辑保留
                    for pattern, progress in progress_patterns.items():
                        if pattern in line:
                            self.progress_signal.emit(progress)
                            break
            
            self.process.wait()
            
            # 新增：输出返回码和stderr（如果有）
            self.output_signal.emit(f"\n命令执行完成，返回码: {self.process.returncode}")
            if self.process.returncode != 0:
                self.output_signal.emit("❌ 命令执行失败！请检查Python解释器路径和PyInstaller是否安装\n")
                self.finished_signal.emit(False, f"返回码: {self.process.returncode}")
            else:
                self.output_signal.emit("\n✅ Packaging completed successfully!\n")
                self.finished_signal.emit(True, "Packaging successful")
                self.progress_signal.emit(100)
                
        except Exception as e:
            # 增强：输出完整的异常栈信息
            import traceback
            error_msg = f"\n❌ 详细错误信息:\n{traceback.format_exc()}\n"
            self.output_signal.emit(error_msg)
            self.finished_signal.emit(False, str(e))
    
    def _build_command(self):
        """Build PyInstaller command"""
        # 修复：打包成EXE时，sys.executable是EXE文件，需手动指定Python解释器
        import shutil
        python_exe = shutil.which("python") or shutil.which("python3")
        
        # 方案2：如果环境变量获取失败，让用户在设置中指定
        if hasattr(self, 'parent') and hasattr(self.parent, 'settings') and self.parent.settings.get('python_path'):
            python_exe = self.parent.settings['python_path']
        
        if not python_exe:
            raise RuntimeError("未找到Python解释器，请在设置中指定Python路径")
        
        cmd = [python_exe, '-m', 'PyInstaller']
        
        # Basic options
        if self.options.get('onefile'):
            cmd.append('--onefile')
        else:
            cmd.append('--onedir')
        
        if self.options.get('console', True):
            cmd.append('--console')
        else:
            cmd.append('--windowed')
        
        if self.options.get('noconfirm'):
            cmd.append('--noconfirm')
        
        if self.options.get('clean'):
            cmd.append('--clean')
        
        # Output directories
        if self.options.get('distpath'):
            cmd.extend(['--distpath', self.options['distpath']])
        
        if self.options.get('workpath'):
            cmd.extend(['--workpath', self.options['workpath']])
        
        if self.options.get('specpath'):
            cmd.extend(['--specpath', self.options['specpath']])
        
        # Name
        if self.options.get('name'):
            cmd.extend(['--name', self.options['name']])
        
        # Icon
        if self.options.get('icon') and os.path.exists(self.options['icon']):
            cmd.extend(['--icon', self.options['icon']])
        
        # Version file
        if self.options.get('version_file') and os.path.exists(self.options['version_file']):
            cmd.extend(['--version-file', self.options['version_file']])
        
        # UPX directory
        if self.options.get('upx_dir') and os.path.exists(self.options['upx_dir']):
            cmd.extend(['--upx-dir', self.options['upx_dir']])
        
        # Add data files
        for data_file in self.options.get('data_files', []):
            if data_file.strip():
                cmd.extend(['--add-data', data_file])
        
        # Add hidden imports
        for hidden_import in self.options.get('hidden_imports', []):
            if hidden_import.strip():
                cmd.extend(['--hidden-import', hidden_import])
        
        # Exclude modules
        for exclude in self.options.get('excludes', []):
            if exclude.strip():
                cmd.extend(['--exclude-module', exclude])
        
        # Python script path
        cmd.append(self.script_path)
        
        return cmd
    
    def stop(self):
        """Stop packaging"""
        self.is_running = False
        if self.process:
            self.process.terminate()


class SettingsDialog(QDialog):
    """Settings dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle(self._tr('settings'))
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        
        # Basic settings
        basic_tab = QWidget()
        basic_layout = QGridLayout(basic_tab)
        
        self.pyinstaller_path = QLineEdit()
        self.pyinstaller_path.setPlaceholderText(self._tr('auto_detect'))
        browse_btn = QPushButton(self._tr('browse'))
        browse_btn.clicked.connect(lambda: self.browse_file(self.pyinstaller_path))
        
        basic_layout.addWidget(QLabel(self._tr('pyinstaller_path')), 0, 0)
        basic_layout.addWidget(self.pyinstaller_path, 0, 1)
        basic_layout.addWidget(browse_btn, 0, 2)
        
        self.upx_path = QLineEdit()
        self.upx_path.setPlaceholderText(self._tr('optional'))
        upx_browse = QPushButton(self._tr('browse'))
        upx_browse.clicked.connect(lambda: self.browse_folder(self.upx_path))
        
        basic_layout.addWidget(QLabel(self._tr('upx_directory')), 1, 0)
        basic_layout.addWidget(self.upx_path, 1, 1)
        basic_layout.addWidget(upx_browse, 1, 2)
        
        self.work_dir = QLineEdit()
        work_browse = QPushButton(self._tr('browse'))
        work_browse.clicked.connect(lambda: self.browse_folder(self.work_dir))
        
        basic_layout.addWidget(QLabel(self._tr('working_directory')), 2, 0)
        basic_layout.addWidget(self.work_dir, 2, 1)
        basic_layout.addWidget(work_browse, 2, 2)
        
        basic_layout.setRowStretch(3, 1)
        
        # Advanced settings
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        
        self.strip_check = QCheckBox(self._tr('enable_code_stripping'))
        self.strip_check.setToolTip(self._tr('remove_debug_symbols'))
        
        self.upx_check = QCheckBox(self._tr('enable_upx_compression'))
        self.upx_check.setToolTip(self._tr('compress_executable_with_upx'))
        
        self.optimize_level = QSpinBox()
        self.optimize_level.setRange(0, 2)
        self.optimize_level.setValue(1)
        
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel(self._tr('optimization_level')))
        opt_layout.addWidget(self.optimize_level)
        opt_layout.addStretch()
        
        advanced_layout.addWidget(self.strip_check)
        advanced_layout.addWidget(self.upx_check)
        advanced_layout.addLayout(opt_layout)
        advanced_layout.addStretch()
        
        # Environment settings
        env_tab = QWidget()
        env_layout = QVBoxLayout(env_tab)
        
        self.python_path = QLineEdit()
        python_browse = QPushButton(self._tr('browse'))
        python_browse.clicked.connect(lambda: self.browse_file(self.python_path))
        
        python_layout = QHBoxLayout()
        python_layout.addWidget(QLabel(self._tr('python_interpreter')))
        python_layout.addWidget(self.python_path)
        python_layout.addWidget(python_browse)
        
        self.virtual_env = QCheckBox(self._tr('use_virtual_environment'))
        
        env_layout.addLayout(python_layout)
        env_layout.addWidget(self.virtual_env)
        env_layout.addStretch()
        
        tabs.addTab(basic_tab, self._tr('basic_settings'))
        tabs.addTab(advanced_tab, self._tr('advanced_settings'))
        tabs.addTab(env_tab, self._tr('environment_settings'))
        
        layout.addWidget(tabs)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Load saved settings
        self.load_settings()
    
    def _tr(self, key):
        """Translate text based on parent's language"""
        if self.parent and hasattr(self.parent, 'translations') and hasattr(self.parent, 'language'):
            return self.parent.translations[self.parent.language].get(key, key)
        return key
    
    def browse_file(self, line_edit):
        """Browse files"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)
    
    def browse_folder(self, line_edit):
        """Browse folders"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            line_edit.setText(folder_path)
    
    def load_settings(self):
        """Load settings"""
        settings_file = Path.home() / '.pypacker_settings.json'
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.pyinstaller_path.setText(settings.get('pyinstaller_path', ''))
                    self.upx_path.setText(settings.get('upx_path', ''))
                    self.work_dir.setText(settings.get('work_dir', ''))
                    self.python_path.setText(settings.get('python_path', ''))
                    self.strip_check.setChecked(settings.get('strip', False))
                    self.upx_check.setChecked(settings.get('upx', False))
                    self.optimize_level.setValue(settings.get('optimize', 1))
                    self.virtual_env.setChecked(settings.get('virtual_env', False))
            except:
                pass
    
    def save_settings(self):
        """Save settings"""
        settings = {
            'pyinstaller_path': self.pyinstaller_path.text(),
            'upx_path': self.upx_path.text(),
            'work_dir': self.work_dir.text(),
            'python_path': self.python_path.text(),
            'strip': self.strip_check.isChecked(),
            'upx': self.upx_check.isChecked(),
            'optimize': self.optimize_level.value(),
            'virtual_env': self.virtual_env.isChecked()
        }
        
        try:
            with open(Path.home() / '.pypacker_settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except:
            pass


class MainWindow(QMainWindow):
    """Main window"""
    
    def __init__(self):
        super().__init__()
        self.build_worker = None
        self.current_script = None
        self.data_files = []
        self.hidden_imports = []
        self.excludes = []
        self.language = 'zh'  # Default language: Chinese
        self.translations = {
            'zh': {
                'window_title': 'PyPacker - Python编译工具 v1.0',
                'file_menu': '文件',
                'open_file': '打开Python文件',
                'exit': '退出',
                'tools_menu': '工具',
                'settings': '设置',
                'check_pyinstaller': '检查PyInstaller',
                'help_menu': '帮助',
                'about': '关于',
                'usage': '使用说明',
                'python_file': 'Python文件',
                'select_file': '选择要打包的Python文件...',
                'browse': '浏览...',
                'no_file_selected': '未选择文件',
                'basic_options': '基本选项',
                'output_mode': '输出模式:',
                'onefile_mode': '单文件模式',
                'onedir_mode': '目录模式',
                'show_console': '显示控制台窗口',
                'overwrite_output': '覆盖输出目录 (--noconfirm)',
                'clean_temp': '清理临时文件 (--clean)',
                'output_options': '输出选项',
                'program_name': '程序名称:',
                'default_filename': '默认使用文件名',
                'icon_file': '图标文件:',
                'optional': '可选',
                'output_dir': '输出目录:',
                'default_dist': '默认: ./dist',
                'advanced_options': '高级选项',
                'additional_files': '附加文件:',
                'add_file': '添加文件...',
                'clear': '清空',
                'hidden_imports': '隐藏导入:',
                'add_module': '添加模块...',
                'version_info': '版本信息',
                'version_file': '版本文件:',
                'version_file_placeholder': '可选 (*.txt, *.spec)',
                'start_packaging': '开始打包',
                'stop': '停止',
                'packaging_output': '打包输出:',
                'clear_output': '清空',
                'ready': '就绪',
                'browse_python_file': '选择Python文件',
                'browse_icon_file': '选择图标文件',
                'browse_folder': '选择文件夹',
                'browse_version_file': '选择版本文件',
                'select_additional_file': '选择附加文件',
                'select_target_path': '选择目标路径',
                'add_module_title': '添加模块',
                'enter_module_name': '输入模块名称:',
                'file_size': '大小: {size}',
                'console_confirm_title': '确认',
                'console_confirm_message': '无控制台模式适合GUI程序。确定要继续吗？',
                'warning': '警告',
                'select_file_first': '请先选择Python文件',
                'install_pyinstaller': '安装PyInstaller',
                'pyinstaller_not_found': '未找到PyInstaller。是否现在安装？',
                'start_packaging_message': '开始打包...\n',
                'stop_packaging': '用户停止打包',
                'packaging_completed': '打包完成',
                'open_output_dir': '打包成功完成！\n\n是否打开输出目录？',
                'packaging_failed': '打包失败',
                'error_during_packaging': '打包过程中出现错误:\n{message}',
                'installing_pyinstaller': '正在安装PyInstaller...\n',
                'pyinstaller_installed': '✅ PyInstaller安装成功！\n',
                'install_failed': '❌ 安装失败:\n{stderr}\n',
                'install_error': '❌ 安装出错: {error}\n',
                'check_result': '检查结果',
                'pyinstaller_installed_message': '✅ PyInstaller已安装 (版本: {version})',
                'pyinstaller_not_installed': '❌ PyInstaller未安装',
                'about_title': '关于 PyPacker',
                'about_content': '<h2>PyPacker v1.0</h2>\n<p>Python文件编译工具</p>\n<p>基于PyInstaller的图形化打包工具</p>\n<p><br></p>\n<p>功能特点:</p>\n<ul>\n<li>支持单文件/目录模式</li>\n<li>支持控制台/GUI程序</li>\n<li>支持自定义图标</li>\n<li>支持附加文件</li>\n<li>实时输出显示</li>\n</ul>\n<p><br></p>\n<p>Copyright © 2024</p>',
                'usage_title': '使用说明',
                'usage_content': '<b>基本用法:</b><br>\n1. 点击"浏览"选择Python文件<br>\n2. 设置打包选项<br>\n3. 点击"开始打包"<br><br>\n\n<b>选项说明:</b><br>\n• 单文件模式：生成单个exe文件<br>\n• 目录模式：生成包含依赖的目录<br>\n• 控制台窗口：显示命令行窗口<br>\n• 覆盖输出：自动覆盖已有文件<br><br>\n\n<b>高级功能:</b><br>\n• 附加文件：添加程序所需的资源文件<br>\n• 隐藏导入：手动指定需要导入的模块<br>\n• 版本信息：添加文件版本信息<br><br>\n\n<b>快捷键:</b><br>\nCtrl+O：打开文件<br>\nCtrl+Q：退出<br>\nCtrl+,：设置',
                'confirm_exit': '确认退出',
                'packaging_in_progress': '打包正在进行中，确定要退出吗？',
                'language_menu': '语言',
                'chinese': '中文',
                'english': 'English',
                'toolbar_open': '📂 打开',
                'toolbar_start': '▶ 开始打包',
                'toolbar_stop': '⏹ 停止',
                'toolbar_clear': '🗑 清空输出',
                'auto_detect': '自动检测',
                'pyinstaller_path': 'PyInstaller路径:',
                'upx_directory': 'UPX目录:',
                'working_directory': '工作目录:',
                'enable_code_stripping': '启用代码剥离 (--strip)',
                'remove_debug_symbols': '移除调试符号，减小文件大小',
                'enable_upx_compression': '启用UPX压缩',
                'compress_executable_with_upx': '使用UPX压缩可执行文件',
                'optimization_level': '优化级别:',
                'python_interpreter': 'Python解释器:',
                'use_virtual_environment': '使用虚拟环境',
                'basic_settings': '基本设置',
                'advanced_settings': '高级设置',
                'environment_settings': '环境设置'
            },
            'en': {
                'window_title': 'PyPacker - Python File Compilation Tool v1.0',
                'file_menu': 'File',
                'open_file': 'Open Python File',
                'exit': 'Exit',
                'tools_menu': 'Tools',
                'settings': 'Settings',
                'check_pyinstaller': 'Check PyInstaller',
                'help_menu': 'Help',
                'about': 'About',
                'usage': 'Usage',
                'python_file': 'Python File',
                'select_file': 'Select Python file to package...',
                'browse': 'Browse...',
                'no_file_selected': 'No file selected',
                'basic_options': 'Basic Options',
                'output_mode': 'Output Mode:',
                'onefile_mode': 'One File Mode',
                'onedir_mode': 'One Directory Mode',
                'show_console': 'Show Console Window',
                'overwrite_output': 'Overwrite output directory (--noconfirm)',
                'clean_temp': 'Clean temporary files (--clean)',
                'output_options': 'Output Options',
                'program_name': 'Program Name:',
                'default_filename': 'Use filename by default',
                'icon_file': 'Icon File:',
                'optional': 'Optional',
                'output_dir': 'Output Directory:',
                'default_dist': 'Default: ./dist',
                'advanced_options': 'Advanced Options',
                'additional_files': 'Additional Files:',
                'add_file': 'Add File...',
                'clear': 'Clear',
                'hidden_imports': 'Hidden Imports:',
                'add_module': 'Add Module...',
                'version_info': 'Version Info',
                'version_file': 'Version File:',
                'version_file_placeholder': 'Optional (*.txt, *.spec)',
                'start_packaging': 'Start Packaging',
                'stop': 'Stop',
                'packaging_output': 'Packaging Output:',
                'clear_output': 'Clear',
                'ready': 'Ready',
                'browse_python_file': 'Select Python File',
                'browse_icon_file': 'Select Icon File',
                'browse_folder': 'Select Folder',
                'browse_version_file': 'Select Version File',
                'select_additional_file': 'Select Additional File',
                'select_target_path': 'Select Target Path',
                'add_module_title': 'Add Module',
                'enter_module_name': 'Enter module name:',
                'file_size': 'Size: {size}',
                'console_confirm_title': 'Confirm',
                'console_confirm_message': 'No console mode is suitable for GUI programs. Are you sure you want to continue?',
                'warning': 'Warning',
                'select_file_first': 'Please select a Python file first',
                'install_pyinstaller': 'Install PyInstaller',
                'pyinstaller_not_found': 'PyInstaller not found. Do you want to install it now?',
                'start_packaging_message': 'Starting packaging...\n',
                'stop_packaging': 'User stopped packaging',
                'packaging_completed': 'Packaging completed',
                'open_output_dir': 'Packaging completed successfully!\n\nDo you want to open the output directory?',
                'packaging_failed': 'Packaging failed',
                'error_during_packaging': 'Error occurred during packaging:\n{message}',
                'installing_pyinstaller': 'Installing PyInstaller...\n',
                'pyinstaller_installed': '✅ PyInstaller installed successfully!\n',
                'install_failed': '❌ Installation failed:\n{stderr}\n',
                'install_error': '❌ Installation error: {error}\n',
                'check_result': 'Check Result',
                'pyinstaller_installed_message': '✅ PyInstaller is installed (version: {version})',
                'pyinstaller_not_installed': '❌ PyInstaller is not installed',
                'about_title': 'About PyPacker',
                'about_content': '<h2>PyPacker v1.0</h2>\n<p>Python File Compilation Tool</p>\n<p>Graphical packaging tool based on PyInstaller</p>\n<p><br></p>\n<p>Features:</p>\n<ul>\n<li>Support single file/directory mode</li>\n<li>Support console/GUI programs</li>\n<li>Support custom icons</li>\n<li>Support additional files</li>\n<li>Real-time output display</li>\n</ul>\n<p><br></p>\n<p>Copyright © 2024</p>',
                'usage_title': 'Usage',
                'usage_content': '<b>Basic Usage:</b><br>\n1. Click "Browse" to select a Python file<br>\n2. Set packaging options<br>\n3. Click "Start Packaging"<br><br>\n\n<b>Option Explanations:</b><br>\n• One File Mode: Generate a single exe file<br>\n• One Directory Mode: Generate a directory with dependencies<br>\n• Console Window: Show command line window<br>\n• Overwrite Output: Automatically overwrite existing files<br><br>\n\n<b>Advanced Features:</b><br>\n• Additional Files: Add resource files needed by the program<br>\n• Hidden Imports: Manually specify modules to import<br>\n• Version Info: Add file version information<br><br>\n\n<b>Shortcuts:</b><br>\nCtrl+O: Open file<br>\nCtrl+Q: Exit<br>\nCtrl+, : Settings',
                'confirm_exit': 'Confirm Exit',
                'packaging_in_progress': 'Packaging is in progress. Are you sure you want to exit?',
                'language_menu': 'Language',
                'chinese': '中文',
                'english': 'English',
                'toolbar_open': '📂 Open',
                'toolbar_start': '▶ Start Packaging',
                'toolbar_stop': '⏹ Stop',
                'toolbar_clear': '🗑 Clear Output',
                'auto_detect': 'Auto-detect',
                'pyinstaller_path': 'PyInstaller Path:',
                'upx_directory': 'UPX Directory:',
                'working_directory': 'Working Directory:',
                'enable_code_stripping': 'Enable code stripping (--strip)',
                'remove_debug_symbols': 'Remove debug symbols, reduce file size',
                'enable_upx_compression': 'Enable UPX compression',
                'compress_executable_with_upx': 'Compress executable with UPX',
                'optimization_level': 'Optimization Level:',
                'python_interpreter': 'Python Interpreter:',
                'use_virtual_environment': 'Use virtual environment',
                'basic_settings': 'Basic Settings',
                'advanced_settings': 'Advanced Settings',
                'environment_settings': 'Environment Settings'
            }
        }
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle(self._tr('window_title'))
        self.setMinimumSize(820, 850)  # 增加窗口宽度
        
        # Clear existing UI elements
        self.clear_ui_elements()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create tool bar
        self.create_tool_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Settings
        left_panel = QWidget()
        left_panel.setMaximumWidth(450)  # 增加左侧面板宽度
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # File selection group
        file_group = QGroupBox(self._tr('python_file'))
        file_layout = QVBoxLayout(file_group)
        
        file_select_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText(self._tr('select_file'))
        self.file_path.textChanged.connect(self.on_file_selected)
        browse_btn = QPushButton(self._tr('browse'))
        browse_btn.clicked.connect(self.browse_file)
        file_select_layout.addWidget(self.file_path)
        file_select_layout.addWidget(browse_btn)
        
        file_info_layout = QHBoxLayout()
        self.file_info_label = QLabel(self._tr('no_file_selected'))
        self.file_info_label.setStyleSheet("color: gray;")
        file_info_layout.addWidget(self.file_info_label)
        
        file_layout.addLayout(file_select_layout)
        file_layout.addLayout(file_info_layout)
        left_layout.addWidget(file_group)
        
        # Basic options group
        basic_group = QGroupBox(self._tr('basic_options'))
        basic_layout = QGridLayout(basic_group)
        
        self.onefile_radio = QRadioButton(self._tr('onefile_mode'))
        self.onefile_radio.setChecked(True)
        self.onedir_radio = QRadioButton(self._tr('onedir_mode'))
        
        mode_group = QButtonGroup()
        mode_group.addButton(self.onefile_radio)
        mode_group.addButton(self.onedir_radio)
        
        basic_layout.addWidget(QLabel(self._tr('output_mode')), 0, 0)
        basic_layout.addWidget(self.onefile_radio, 0, 1)
        basic_layout.addWidget(self.onedir_radio, 0, 2)
        
        self.console_check = QCheckBox(self._tr('show_console'))
        self.console_check.setChecked(True)
        self.console_check.toggled.connect(self.on_console_toggled)
        basic_layout.addWidget(self.console_check, 1, 0, 1, 3)
        
        self.noconfirm_check = QCheckBox(self._tr('overwrite_output'))
        self.noconfirm_check.setChecked(True)
        basic_layout.addWidget(self.noconfirm_check, 2, 0, 1, 3)
        
        self.clean_check = QCheckBox(self._tr('clean_temp'))
        self.clean_check.setChecked(True)
        basic_layout.addWidget(self.clean_check, 3, 0, 1, 3)
        
        left_layout.addWidget(basic_group)
        
        # Output options group
        output_group = QGroupBox(self._tr('output_options'))
        output_layout = QGridLayout(output_group)
        
        output_layout.addWidget(QLabel(self._tr('program_name')), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self._tr('default_filename'))
        output_layout.addWidget(self.name_edit, 0, 1)
        
        output_layout.addWidget(QLabel(self._tr('icon_file')), 1, 0)
        icon_layout = QHBoxLayout()
        self.icon_path = QLineEdit()
        self.icon_path.setPlaceholderText(self._tr('optional'))
        icon_browse = QPushButton(self._tr('browse'))
        icon_browse.clicked.connect(lambda: self.browse_icon())
        icon_layout.addWidget(self.icon_path)
        icon_layout.addWidget(icon_browse)
        output_layout.addLayout(icon_layout, 1, 1)
        
        output_layout.addWidget(QLabel(self._tr('output_dir')), 2, 0)
        dist_layout = QHBoxLayout()
        self.dist_path = QLineEdit()
        self.dist_path.setPlaceholderText(self._tr('default_dist'))
        dist_browse = QPushButton(self._tr('browse'))
        dist_browse.clicked.connect(lambda: self.browse_folder(self.dist_path))
        dist_layout.addWidget(self.dist_path)
        dist_layout.addWidget(dist_browse)
        output_layout.addLayout(dist_layout, 2, 1)
        
        left_layout.addWidget(output_group)
        
        # Advanced options group
        advanced_group = QGroupBox(self._tr('advanced_options'))
        advanced_layout = QVBoxLayout(advanced_group)
        
        # Data files
        data_label = QLabel(self._tr('additional_files'))
        data_btn_layout = QHBoxLayout()
        add_data_btn = QPushButton(self._tr('add_file'))
        add_data_btn.clicked.connect(self.add_data_file)
        clear_data_btn = QPushButton(self._tr('clear'))
        clear_data_btn.clicked.connect(self.clear_data_files)
        data_btn_layout.addWidget(add_data_btn)
        data_btn_layout.addWidget(clear_data_btn)
        
        self.data_list = QListWidget()
        self.data_list.setMaximumHeight(80)
        
        advanced_layout.addWidget(data_label)
        advanced_layout.addLayout(data_btn_layout)
        advanced_layout.addWidget(self.data_list)
        
        # Hidden imports
        import_label = QLabel(self._tr('hidden_imports'))
        import_btn_layout = QHBoxLayout()
        add_import_btn = QPushButton(self._tr('add_module'))
        add_import_btn.clicked.connect(self.add_hidden_import)
        clear_import_btn = QPushButton(self._tr('clear'))
        clear_import_btn.clicked.connect(self.clear_hidden_imports)
        import_btn_layout.addWidget(add_import_btn)
        import_btn_layout.addWidget(clear_import_btn)
        
        self.import_list = QListWidget()
        self.import_list.setMaximumHeight(80)
        
        advanced_layout.addWidget(import_label)
        advanced_layout.addLayout(import_btn_layout)
        advanced_layout.addWidget(self.import_list)
        
        left_layout.addWidget(advanced_group)
        
        # Version info
        version_group = QGroupBox(self._tr('version_info'))
        version_layout = QGridLayout(version_group)
        
        version_layout.addWidget(QLabel(self._tr('version_file')), 0, 0)
        version_file_layout = QHBoxLayout()
        self.version_file = QLineEdit()
        self.version_file.setPlaceholderText(self._tr('version_file_placeholder'))
        version_browse = QPushButton(self._tr('browse'))
        version_browse.clicked.connect(lambda: self.browse_version_file())
        version_file_layout.addWidget(self.version_file)
        version_file_layout.addWidget(version_browse)
        version_layout.addLayout(version_file_layout, 0, 1)
        
        left_layout.addWidget(version_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        self.build_btn = QPushButton(self._tr('start_packaging'))
        self.build_btn.setEnabled(False)
        self.build_btn.setMinimumHeight(40)
        self.build_btn.setMinimumWidth(120)  # 设置最小宽度
        self.build_btn.clicked.connect(self.start_build)
        
        self.stop_btn = QPushButton(self._tr('stop'))
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(40)  # 设置相同的高度
        self.stop_btn.setMinimumWidth(120)  # 设置相同的宽度
        self.stop_btn.clicked.connect(self.stop_build)
        
        btn_layout.addWidget(self.build_btn)
        btn_layout.addWidget(self.stop_btn)
        left_layout.addLayout(btn_layout)
        
        left_layout.addStretch()
        
        # Right panel - Output
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Output title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel(self._tr('packaging_output')))
        
        self.clear_output_btn = QPushButton(self._tr('clear_output'))
        self.clear_output_btn.clicked.connect(self.clear_output)
        title_layout.addWidget(self.clear_output_btn)
        title_layout.addStretch()
        
        right_layout.addLayout(title_layout)
        
        # Output text box
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        right_layout.addWidget(self.output_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self._tr('ready'))
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # Apply style
        self.apply_style()
    
    def clear_ui_elements(self):
        """Clear existing UI elements before reinitializing"""
        # Clear menu bar
        menubar = self.menuBar()
        while menubar.actions():
            action = menubar.actions()[0]
            if action.menu():
                action.menu().clear()
            menubar.removeAction(action)
        
        # Clear toolbars
        for toolbar in self.findChildren(QToolBar):
            self.removeToolBar(toolbar)
            toolbar.deleteLater()
        
        # Clear status bar
        if hasattr(self, 'status_bar'):
            self.statusBar().clearMessage()
    
    def _tr(self, key):
        """Translate text based on current language"""
        return self.translations[self.language].get(key, key)
    
    def switch_language(self, lang):
        """Switch application language"""
        self.language = lang
        # Reinitialize UI with new language
        self.init_ui()
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu(self._tr('file_menu'))
        
        open_action = QAction(self._tr('open_file'), self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.browse_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(self._tr('exit'), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Language menu
        lang_menu = menubar.addMenu(self._tr('language_menu'))
        
        zh_action = QAction(self._tr('chinese'), self)
        zh_action.triggered.connect(lambda: self.switch_language('zh'))
        lang_menu.addAction(zh_action)
        
        en_action = QAction(self._tr('english'), self)
        en_action.triggered.connect(lambda: self.switch_language('en'))
        lang_menu.addAction(en_action)
        
        # Tools menu
        tools_menu = menubar.addMenu(self._tr('tools_menu'))
        
        settings_action = QAction(self._tr('settings'), self)
        settings_action.setShortcut("Ctrl+," )
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        check_pyinstaller = QAction(self._tr('check_pyinstaller'), self)
        check_pyinstaller.triggered.connect(self.check_pyinstaller)
        tools_menu.addAction(check_pyinstaller)
        
        # Help menu
        help_menu = menubar.addMenu(self._tr('help_menu'))
        
        about_action = QAction(self._tr('about'), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        usage_action = QAction(self._tr('usage'), self)
        usage_action.triggered.connect(self.show_usage)
        help_menu.addAction(usage_action)
    
    def create_tool_bar(self):
        """Create tool bar"""
        toolbar = QToolBar(self._tr('window_title'))
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Using text buttons since no icons are available
        open_btn = QAction(self._tr('toolbar_open'), self)
        open_btn.triggered.connect(self.browse_file)
        toolbar.addAction(open_btn)
        
        toolbar.addSeparator()
        
        build_btn = QAction(self._tr('toolbar_start'), self)
        build_btn.triggered.connect(self.start_build)
        toolbar.addAction(build_btn)
        
        stop_btn = QAction(self._tr('toolbar_stop'), self)
        stop_btn.triggered.connect(self.stop_build)
        toolbar.addAction(stop_btn)
        
        toolbar.addSeparator()
        
        clear_btn = QAction(self._tr('toolbar_clear'), self)
        clear_btn.triggered.connect(self.clear_output)
        toolbar.addAction(clear_btn)
    
    def apply_style(self):
        """Apply style"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                padding: 5px 15px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: #ffffff;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
            QPushButton:pressed {
                background-color: #d4d4d4;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #a0a0a0;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 3px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
    
    def browse_file(self):
        """Browse Python files"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._tr('browse_python_file'), "", "Python files (*.py);;All files (*)"
        )
        if file_path:
            self.file_path.setText(file_path)
    
    def browse_icon(self):
        """Browse icon files"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._tr('browse_icon_file'), "", "Icon files (*.ico);;All files (*)"
        )
        if file_path:
            self.icon_path.setText(file_path)
    
    def browse_folder(self, line_edit):
        """Browse folders"""
        folder_path = QFileDialog.getExistingDirectory(self, self._tr('browse_folder'))
        if folder_path:
            line_edit.setText(folder_path)
    
    def browse_version_file(self):
        """Browse version files"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._tr('browse_version_file'), "", "Text files (*.txt);;Spec files (*.spec);;All files (*)"
        )
        if file_path:
            self.version_file.setText(file_path)
    
    def add_data_file(self):
        """Add data files"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._tr('select_additional_file'), "", "All files (*)"
        )
        if file_path:
            target_path = QFileDialog.getExistingDirectory(self, self._tr('select_target_path'))
            if target_path:
                # Format: source_file;target_path
                data_item = f"{file_path};{target_path}"
                self.data_files.append(data_item)
                self.data_list.addItem(f"{os.path.basename(file_path)} → {target_path}")
    
    def clear_data_files(self):
        """Clear data files"""
        self.data_files.clear()
        self.data_list.clear()
    
    def add_hidden_import(self):
        """Add hidden imports"""
        module_name, ok = QInputDialog.getText(self, self._tr('add_module_title'), self._tr('enter_module_name'))
        if ok and module_name:
            self.hidden_imports.append(module_name)
            self.import_list.addItem(module_name)
    
    def clear_hidden_imports(self):
        """Clear hidden imports"""
        self.hidden_imports.clear()
        self.import_list.clear()
    
    def on_file_selected(self, file_path):
        """Handle file selection"""
        if os.path.exists(file_path):
            self.current_script = file_path
            self.build_btn.setEnabled(True)
            
            # Get file info
            file_size = os.path.getsize(file_path)
            file_size_str = self.format_size(file_size)
            self.file_info_label.setText(self._tr('file_size').format(size=file_size_str))
            
            # Auto set program name
            if not self.name_edit.text():
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                self.name_edit.setText(base_name)
        else:
            self.current_script = None
            self.build_btn.setEnabled(False)
            self.file_info_label.setText(self._tr('no_file_selected'))
    
    def on_console_toggled(self, checked):
        """Handle console option toggle"""
        if not checked:
            reply = QMessageBox.question(
                self, self._tr('console_confirm_title'),
                self._tr('console_confirm_message'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.console_check.setChecked(True)
    
    def format_size(self, size):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def start_build(self):
        """Start packaging"""
        if not self.current_script:
            QMessageBox.warning(self, self._tr('warning'), self._tr('select_file_first'))
            return
        
        # Check PyInstaller
        try:
            import PyInstaller
        except ImportError:
            reply = QMessageBox.question(
                self, self._tr('install_pyinstaller'),
                self._tr('pyinstaller_not_found'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.install_pyinstaller()
            return
        
        # Collect options
        options = {
            'onefile': self.onefile_radio.isChecked(),
            'console': self.console_check.isChecked(),
            'noconfirm': self.noconfirm_check.isChecked(),
            'clean': self.clean_check.isChecked(),
            'name': self.name_edit.text() or None,
            'icon': self.icon_path.text() or None,
            'distpath': self.dist_path.text() or None,
            'version_file': self.version_file.text() or None,
            'data_files': self.data_files,
            'hidden_imports': self.hidden_imports,
            'excludes': self.excludes
        }
        
        # 新增：读取设置中的Python路径
        settings_file = Path.home() / '.pypacker_settings.json'
        self.settings = {}
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except:
                pass
        
        # Start packaging thread
        self.build_worker = BuildWorker(self.current_script, options)
        self.build_worker.parent = self  # 让BuildWorker能访问MainWindow的settings
        self.build_worker.output_signal.connect(self.append_output)
        self.build_worker.finished_signal.connect(self.on_build_finished)
        self.build_worker.progress_signal.connect(self.update_progress)
        
        # Update UI status
        self.build_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.clear_output()
        self.append_output(self._tr('start_packaging_message'))
        
        self.build_worker.start()
    
    def stop_build(self):
        """Stop packaging"""
        if self.build_worker and self.build_worker.isRunning():
            reply = QMessageBox.question(
                self, self._tr('confirm_exit'),
                self._tr('packaging_in_progress'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.build_worker.stop()
                self.append_output(f"\n⏹ {self._tr('stop_packaging')}\n")
                self.on_build_finished(False, self._tr('stop_packaging'))
    
    def on_build_finished(self, success, message):
        """Handle packaging completion"""
        self.build_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self.status_bar.showMessage(self._tr('packaging_completed'))
            self.progress_bar.setValue(100)
            
            # Prompt to open output directory
            dist_path = self.dist_path.text() or os.path.join(os.getcwd(), 'dist')
            reply = QMessageBox.question(
                self, self._tr('packaging_completed'),
                self._tr('open_output_dir'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(dist_path) if sys.platform == 'win32' else os.system(f'open "{dist_path}"')
        else:
            self.status_bar.showMessage(f"{self._tr('packaging_failed')}: {message}")
            QMessageBox.critical(self, self._tr('packaging_failed'), self._tr('error_during_packaging').format(message=message))
        
        # 重置进度条
        QTimer.singleShot(1000, lambda: self.progress_bar.setValue(0))
    
    def append_output(self, text):
        """Append output text"""
        self.output_text.moveCursor(QTextCursor.MoveOperation.End)
        self.output_text.insertPlainText(text)
        self.output_text.ensureCursorVisible()
    
    def clear_output(self):
        """Clear output"""
        self.output_text.clear()
    
    def update_progress(self, value):
        """Update progress"""
        self.progress_bar.setValue(value)
    
    def install_pyinstaller(self):
        """Install PyInstaller"""
        self.clear_output()
        self.append_output(self._tr('installing_pyinstaller'))
        
        def install():
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.append_output(self._tr('pyinstaller_installed'))
                else:
                    self.append_output(self._tr('install_failed').format(stderr=result.stderr))
            except Exception as e:
                self.append_output(self._tr('install_error').format(error=str(e)))
        
        thread = threading.Thread(target=install)
        thread.start()
    
    def check_pyinstaller(self):
        """Check PyInstaller"""
        try:
            import PyInstaller
            version = getattr(PyInstaller, '__version__', 'Unknown')
            QMessageBox.information(self, self._tr('check_result'), self._tr('pyinstaller_installed_message').format(version=version))
        except ImportError:
            QMessageBox.information(self, self._tr('check_result'), self._tr('pyinstaller_not_installed'))
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save_settings()
            # Apply settings
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, self._tr('about_title'),
            self._tr('about_content')
        )
    
    def show_usage(self):
        """Show usage dialog"""
        QMessageBox.information(
            self, self._tr('usage_title'),
            self._tr('usage_content')
        )
    
    def closeEvent(self, event):
        """Handle close event"""
        if self.build_worker and self.build_worker.isRunning():
            reply = QMessageBox.question(
                self, self._tr('confirm_exit'),
                self._tr('packaging_in_progress'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.build_worker.stop()
                self.build_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application information
    app.setApplicationName("PyPacker")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("PyPacker")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    # Check required libraries
    try:
        from PyQt6.QtWidgets import QInputDialog
    except ImportError:
        print("Please install PyQt6 first: pip install PyQt6")
        sys.exit(1)
    
    main()