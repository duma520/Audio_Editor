#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import wave
import threading
import time
from pathlib import Path
from datetime import datetime

import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize, high_pass_filter, low_pass_filter
from pydub.playback import play

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QMessageBox,
    QProgressBar, QFrame, QSplitter, QScrollArea, QGroupBox,
    QGridLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSettings, QSize
from PySide6.QtGui import QIcon, QFont, QPalette, QColor
from PySide6.QtMultimedia import QAudioOutput, QAudioFormat, QAudioSource
from PySide6.QtMultimedia import QMediaDevices

class AudioProcessingThreadUnique(QThread):
    """音频处理线程类"""
    progress_updated = Signal(int)
    processing_finished = Signal(object)
    error_occurred = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.audio_data = None
        self.operation_type = ""
        self.parameters = {}
        self._is_running = True
        
    def set_operation(self, audio_data, operation_type, parameters=None):
        """设置要执行的操作"""
        self.audio_data = audio_data
        self.operation_type = operation_type
        self.parameters = parameters or {}
        self._is_running = True
        
    def run(self):
        """执行音频处理"""
        try:
            if not self.audio_data:
                self.error_occurred.emit("没有音频数据")
                return
                
            result = None
            
            if self.operation_type == "trim":
                result = self._trim_audio()
            elif self.operation_type == "fade_in":
                result = self._fade_in()
            elif self.operation_type == "fade_out":
                result = self._fade_out()
            elif self.operation_type == "volume":
                result = self._adjust_volume()
            elif self.operation_type == "speed":
                result = self._change_speed()
            elif self.operation_type == "normalize":
                result = self._normalize_audio()
            elif self.operation_type == "highpass":
                result = self._highpass_filter()
            elif self.operation_type == "lowpass":
                result = self._lowpass_filter()
            elif self.operation_type == "export":
                result = self._export_audio()
            else:
                result = self.audio_data
                
            if self._is_running:
                self.processing_finished.emit(result)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
            
    def stop(self):
        """停止处理"""
        self._is_running = False
        
    def _trim_audio(self):
        """裁剪音频"""
        start_ms = self.parameters.get('start', 0)
        end_ms = self.parameters.get('end', len(self.audio_data))
        duration = end_ms - start_ms
        
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        return self.audio_data[start_ms:end_ms]
        
    def _fade_in(self):
        """淡入效果"""
        fade_duration = self.parameters.get('duration', 1000)
        
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        return self.audio_data.fade_in(fade_duration)
        
    def _fade_out(self):
        """淡出效果"""
        fade_duration = self.parameters.get('duration', 1000)
        
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        return self.audio_data.fade_out(fade_duration)
        
    def _adjust_volume(self):
        """调整音量"""
        gain_db = self.parameters.get('gain', 0)
        
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        return self.audio_data + gain_db
        
    def _change_speed(self):
        """改变速度"""
        speed_factor = self.parameters.get('speed', 1.0)
        
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        return self.audio_data._spawn(self.audio_data.raw_data, 
                                       overrides={"frame_rate": int(self.audio_data.frame_rate * speed_factor)})
        
    def _normalize_audio(self):
        """标准化音频"""
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        return normalize(self.audio_data)
        
    def _highpass_filter(self):
        """高通滤波"""
        cutoff_freq = self.parameters.get('cutoff', 1000)
        
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        return high_pass_filter(self.audio_data, cutoff_freq)
        
    def _lowpass_filter(self):
        """低通滤波"""
        cutoff_freq = self.parameters.get('cutoff', 1000)
        
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        return low_pass_filter(self.audio_data, cutoff_freq)
        
    def _export_audio(self):
        """导出音频"""
        filepath = self.parameters.get('filepath', '')
        format_type = self.parameters.get('format', 'mp3')
        
        for i in range(101):
            if not self._is_running:
                return None
            time.sleep(0.01)
            self.progress_updated.emit(i)
            
        self.audio_data.export(filepath, format=format_type)
        return self.audio_data

class WaveformWidgetUnique(QWidget):
    """波形显示控件"""
    def __init__(self):
        super().__init__()
        self.audio_data = None
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
        
    def set_audio_data(self, audio_data):
        """设置音频数据"""
        self.audio_data = audio_data
        self.update()
        
    def paintEvent(self, event):
        """绘制波形"""
        if not self.audio_data:
            return
            
        from PySide6.QtGui import QPainter, QPen, QLinearGradient
        from PySide6.QtCore import QPoint
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建渐变色
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(52, 152, 219))
        gradient.setColorAt(1, QColor(155, 89, 182))
        
        pen = QPen(gradient, 2)
        painter.setPen(pen)
        
        # 获取音频样本
        samples = np.array(self.audio_data.get_array_of_samples())
        if len(samples) == 0:
            return
            
        # 下采样以适应宽度
        width = self.width()
        if len(samples) > width:
            indices = np.linspace(0, len(samples) - 1, width, dtype=int)
            samples = samples[indices]
            
        # 归一化
        max_val = max(abs(samples.max()), abs(samples.min()))
        if max_val > 0:
            samples = samples / max_val
            
        # 绘制波形
        center_y = self.height() / 2
        points = []
        for x, val in enumerate(samples):
            y = center_y - (val * center_y * 0.8)
            points.append(QPoint(x, int(y)))
            
        painter.drawPolyline(points)

class AudioPlayerThreadUnique(QThread):
    """音频播放线程"""
    position_changed = Signal(int)
    playback_finished = Signal()
    
    def __init__(self):
        super().__init__()
        self.audio_data = None
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0
        
    def set_audio(self, audio_data):
        """设置要播放的音频"""
        self.audio_data = audio_data
        
    def run(self):
        """播放音频"""
        if not self.audio_data:
            return
            
        self.is_playing = True
        self.is_paused = False
        
        # 模拟播放过程
        duration = len(self.audio_data)
        step = duration / 100  # 1% 的进度
        
        while self.is_playing and self.current_position < duration:
            if not self.is_paused:
                time.sleep(0.01)  # 模拟播放时间
                self.current_position += step
                self.position_changed.emit(int(self.current_position))
            else:
                time.sleep(0.1)
                
        if self.current_position >= duration:
            self.playback_finished.emit()
            self.current_position = 0
            
    def pause(self):
        """暂停播放"""
        self.is_paused = True
        
    def resume(self):
        """恢复播放"""
        self.is_paused = False
        
    def stop(self):
        """停止播放"""
        self.is_playing = False
        self.current_position = 0

class MainWindowUnique(QMainWindow):
    """主窗口类"""
    
    # 定义信号
    audio_loaded_signal = Signal(object)
    processing_started_signal = Signal()
    processing_finished_signal = Signal()
    
    def __init__(self):
        super().__init__()
        
        # 初始化变量
        self.current_audio = None
        self.original_audio = None
        self.audio_file_path = ""
        self.settings = QSettings("AudioEditor", "Settings")
        self.processing_thread = AudioProcessingThreadUnique()
        self.player_thread = AudioPlayerThreadUnique()
        
        # 设置窗口属性
        self.setWindowTitle("音频编辑器")
        self.setMinimumSize(1000, 700)
        
        # 设置图标
        self._setup_icon_unique()
        
        # 创建UI
        self._create_ui_unique()
        
        # 连接信号
        self._connect_signals_unique()
        
        # 加载设置
        self._load_settings_unique()
        
        # 应用样式
        self._apply_style_unique()
        
    def _setup_icon_unique(self):
        """设置窗口图标"""
        icon_path = Path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
            
    def _create_ui_unique(self):
        """创建UI界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.open_button = QPushButton("打开文件")
        self.open_button.setMinimumHeight(35)
        toolbar_layout.addWidget(self.open_button)
        
        self.save_button = QPushButton("保存")
        self.save_button.setMinimumHeight(35)
        self.save_button.setEnabled(False)
        toolbar_layout.addWidget(self.save_button)
        
        self.export_button = QPushButton("导出")
        self.export_button.setMinimumHeight(35)
        self.export_button.setEnabled(False)
        toolbar_layout.addWidget(self.export_button)
        
        toolbar_layout.addStretch()
        
        self.file_label = QLabel("未选择文件")
        self.file_label.setMinimumHeight(35)
        toolbar_layout.addWidget(self.file_label)
        
        main_layout.addLayout(toolbar_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # 播放控制组
        play_group = QGroupBox("播放控制")
        play_layout = QVBoxLayout()
        
        # 播放按钮
        play_buttons_layout = QHBoxLayout()
        self.play_button = QPushButton("播放")
        self.play_button.setEnabled(False)
        self.play_button.setMinimumHeight(30)
        play_buttons_layout.addWidget(self.play_button)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.setEnabled(False)
        self.pause_button.setMinimumHeight(30)
        play_buttons_layout.addWidget(self.pause_button)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(30)
        play_buttons_layout.addWidget(self.stop_button)
        
        play_layout.addLayout(play_buttons_layout)
        
        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("播放进度:"))
        self.play_progress = QProgressBar()
        self.play_progress.setTextVisible(True)
        self.play_progress.setFormat("%v/%m")
        progress_layout.addWidget(self.play_progress)
        play_layout.addLayout(progress_layout)
        
        # 音量控制
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("音量:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setEnabled(False)
        volume_layout.addWidget(self.volume_slider)
        self.volume_label = QLabel("70%")
        volume_layout.addWidget(self.volume_label)
        play_layout.addLayout(volume_layout)
        
        play_group.setLayout(play_layout)
        left_layout.addWidget(play_group)
        
        # 编辑工具组
        edit_group = QGroupBox("编辑工具")
        edit_layout = QGridLayout()
        edit_layout.setVerticalSpacing(10)
        edit_layout.setHorizontalSpacing(10)
        
        # 裁剪
        edit_layout.addWidget(QLabel("裁剪(ms):"), 0, 0)
        self.trim_start = QSpinBox()
        self.trim_start.setRange(0, 999999)
        self.trim_start.setSuffix(" ms")
        self.trim_start.setEnabled(False)
        edit_layout.addWidget(self.trim_start, 0, 1)
        
        self.trim_end = QSpinBox()
        self.trim_end.setRange(0, 999999)
        self.trim_end.setSuffix(" ms")
        self.trim_end.setEnabled(False)
        edit_layout.addWidget(self.trim_end, 0, 2)
        
        self.trim_button = QPushButton("裁剪")
        self.trim_button.setEnabled(False)
        self.trim_button.setMinimumHeight(25)
        edit_layout.addWidget(self.trim_button, 0, 3)
        
        # 淡入淡出
        edit_layout.addWidget(QLabel("淡入(ms):"), 1, 0)
        self.fade_in = QSpinBox()
        self.fade_in.setRange(0, 10000)
        self.fade_in.setValue(1000)
        self.fade_in.setSuffix(" ms")
        self.fade_in.setEnabled(False)
        edit_layout.addWidget(self.fade_in, 1, 1)
        
        self.fade_in_button = QPushButton("淡入")
        self.fade_in_button.setEnabled(False)
        self.fade_in_button.setMinimumHeight(25)
        edit_layout.addWidget(self.fade_in_button, 1, 2)
        
        edit_layout.addWidget(QLabel("淡出(ms):"), 2, 0)
        self.fade_out = QSpinBox()
        self.fade_out.setRange(0, 10000)
        self.fade_out.setValue(1000)
        self.fade_out.setSuffix(" ms")
        self.fade_out.setEnabled(False)
        edit_layout.addWidget(self.fade_out, 2, 1)
        
        self.fade_out_button = QPushButton("淡出")
        self.fade_out_button.setEnabled(False)
        self.fade_out_button.setMinimumHeight(25)
        edit_layout.addWidget(self.fade_out_button, 2, 2)
        
        # 音量调整
        edit_layout.addWidget(QLabel("音量增益:"), 3, 0)
        self.volume_gain = QSpinBox()
        self.volume_gain.setRange(-60, 60)
        self.volume_gain.setValue(0)
        self.volume_gain.setSuffix(" dB")
        self.volume_gain.setEnabled(False)
        edit_layout.addWidget(self.volume_gain, 3, 1)
        
        self.volume_gain_button = QPushButton("调整音量")
        self.volume_gain_button.setEnabled(False)
        self.volume_gain_button.setMinimumHeight(25)
        edit_layout.addWidget(self.volume_gain_button, 3, 2)
        
        # 速度调整
        edit_layout.addWidget(QLabel("速度系数:"), 4, 0)
        self.speed_factor = QDoubleSpinBox()
        self.speed_factor.setRange(0.5, 2.0)
        self.speed_factor.setValue(1.0)
        self.speed_factor.setSingleStep(0.1)
        self.speed_factor.setEnabled(False)
        edit_layout.addWidget(self.speed_factor, 4, 1)
        
        self.speed_button = QPushButton("调整速度")
        self.speed_button.setEnabled(False)
        self.speed_button.setMinimumHeight(25)
        edit_layout.addWidget(self.speed_button, 4, 2)
        
        # 滤波效果
        edit_layout.addWidget(QLabel("高通滤波:"), 5, 0)
        self.highpass_freq = QSpinBox()
        self.highpass_freq.setRange(20, 20000)
        self.highpass_freq.setValue(1000)
        self.highpass_freq.setSuffix(" Hz")
        self.highpass_freq.setEnabled(False)
        edit_layout.addWidget(self.highpass_freq, 5, 1)
        
        self.highpass_button = QPushButton("高通滤波")
        self.highpass_button.setEnabled(False)
        self.highpass_button.setMinimumHeight(25)
        edit_layout.addWidget(self.highpass_button, 5, 2)
        
        edit_layout.addWidget(QLabel("低通滤波:"), 6, 0)
        self.lowpass_freq = QSpinBox()
        self.lowpass_freq.setRange(20, 20000)
        self.lowpass_freq.setValue(1000)
        self.lowpass_freq.setSuffix(" Hz")
        self.lowpass_freq.setEnabled(False)
        edit_layout.addWidget(self.lowpass_freq, 6, 1)
        
        self.lowpass_button = QPushButton("低通滤波")
        self.lowpass_button.setEnabled(False)
        self.lowpass_button.setMinimumHeight(25)
        edit_layout.addWidget(self.lowpass_button, 6, 2)
        
        # 标准化
        self.normalize_button = QPushButton("标准化音频")
        self.normalize_button.setEnabled(False)
        self.normalize_button.setMinimumHeight(30)
        edit_layout.addWidget(self.normalize_button, 7, 0, 1, 4)
        
        edit_group.setLayout(edit_layout)
        left_layout.addWidget(edit_group)
        
        # 全局进度条
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(QLabel("处理进度:"))
        self.global_progress = QProgressBar()
        self.global_progress.setTextVisible(True)
        progress_layout.addWidget(self.global_progress)
        left_layout.addLayout(progress_layout)
        
        # 添加弹性空间
        left_layout.addStretch()
        
        # 右侧波形显示区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        
        # 波形显示
        waveform_label = QLabel("波形预览")
        waveform_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(waveform_label)
        
        self.waveform_widget = WaveformWidgetUnique()
        right_layout.addWidget(self.waveform_widget)
        
        # 时间信息
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00:00")
        time_layout.addWidget(self.current_time_label)
        
        time_layout.addStretch()
        
        self.total_time_label = QLabel("00:00:00")
        time_layout.addWidget(self.total_time_label)
        right_layout.addLayout(time_layout)
        
        # 添加分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
    def _connect_signals_unique(self):
        """连接信号"""
        # 按钮信号
        self.open_button.clicked.connect(self._open_file_unique)
        self.save_button.clicked.connect(self._save_file_unique)
        self.export_button.clicked.connect(self._export_file_unique)
        
        self.play_button.clicked.connect(self._play_audio_unique)
        self.pause_button.clicked.connect(self._pause_audio_unique)
        self.stop_button.clicked.connect(self._stop_audio_unique)
        
        # 编辑按钮信号
        self.trim_button.clicked.connect(lambda: self._start_processing_unique("trim"))
        self.fade_in_button.clicked.connect(lambda: self._start_processing_unique("fade_in"))
        self.fade_out_button.clicked.connect(lambda: self._start_processing_unique("fade_out"))
        self.volume_gain_button.clicked.connect(lambda: self._start_processing_unique("volume"))
        self.speed_button.clicked.connect(lambda: self._start_processing_unique("speed"))
        self.highpass_button.clicked.connect(lambda: self._start_processing_unique("highpass"))
        self.lowpass_button.clicked.connect(lambda: self._start_processing_unique("lowpass"))
        self.normalize_button.clicked.connect(lambda: self._start_processing_unique("normalize"))
        
        # 滑块信号
        self.volume_slider.valueChanged.connect(self._volume_changed_unique)
        
        # 线程信号
        self.processing_thread.progress_updated.connect(self.global_progress.setValue)
        self.processing_thread.processing_finished.connect(self._processing_finished_unique)
        self.processing_thread.error_occurred.connect(self._show_error_unique)
        
        self.player_thread.position_changed.connect(self._update_play_position_unique)
        self.player_thread.playback_finished.connect(self._playback_finished_unique)
        
        self.audio_loaded_signal.connect(self._audio_loaded_unique)
        self.processing_started_signal.connect(self._processing_started_unique)
        self.processing_finished_signal.connect(self._processing_finished_ui_unique)
        
    def _apply_style_unique(self):
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QSpinBox, QDoubleSpinBox {
                padding: 5px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #bdc3c7;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QLabel {
                color: #2c3e50;
            }
        """)
        
    def _load_settings_unique(self):
        """加载设置"""
        # 加载窗口设置
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        # 加载音量设置
        volume = self.settings.value("volume", 70, type=int)
        self.volume_slider.setValue(volume)
        
        # 加载最近文件
        last_file = self.settings.value("last_file", "")
        if last_file and Path(last_file).exists():
            self.audio_file_path = last_file
            self.file_label.setText(f"上次文件: {Path(last_file).name}")
            
    def _save_settings_unique(self):
        """保存设置"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("volume", self.volume_slider.value())
        self.settings.setValue("last_file", self.audio_file_path)
        
    def closeEvent(self, event):
        """关闭事件"""
        self._save_settings_unique()
        self.processing_thread.stop()
        self.player_thread.stop()
        event.accept()
        
    def _open_file_unique(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.mp3 *.wav *.ogg *.flac *.m4a);;所有文件 (*.*)"
        )
        
        if file_path:
            self.audio_file_path = file_path
            self.file_label.setText(f"正在加载: {Path(file_path).name}")
            
            # 在新线程中加载文件
            threading.Thread(target=self._load_audio_file_unique, args=(file_path,), daemon=True).start()
            
    def _load_audio_file_unique(self, file_path):
        """加载音频文件"""
        try:
            audio = AudioSegment.from_file(file_path)
            self.audio_loaded_signal.emit(audio)
        except Exception as e:
            self._show_error_unique(f"加载文件失败: {str(e)}")
            
    @Slot(object)
    def _audio_loaded_unique(self, audio):
        """音频加载完成"""
        self.original_audio = audio
        self.current_audio = audio
        
        # 更新UI
        self.file_label.setText(f"当前文件: {Path(self.audio_file_path).name}")
        self.save_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.volume_slider.setEnabled(True)
        
        # 启用编辑控件
        self.trim_start.setEnabled(True)
        self.trim_end.setEnabled(True)
        self.trim_button.setEnabled(True)
        self.fade_in.setEnabled(True)
        self.fade_in_button.setEnabled(True)
        self.fade_out.setEnabled(True)
        self.fade_out_button.setEnabled(True)
        self.volume_gain.setEnabled(True)
        self.volume_gain_button.setEnabled(True)
        self.speed_factor.setEnabled(True)
        self.speed_button.setEnabled(True)
        self.highpass_freq.setEnabled(True)
        self.highpass_button.setEnabled(True)
        self.lowpass_freq.setEnabled(True)
        self.lowpass_button.setEnabled(True)
        self.normalize_button.setEnabled(True)
        
        # 设置裁剪范围
        duration_ms = len(audio)
        self.trim_start.setMaximum(duration_ms)
        self.trim_end.setMaximum(duration_ms)
        self.trim_end.setValue(duration_ms)
        
        # 更新波形显示
        self.waveform_widget.set_audio_data(audio)
        
        # 更新时间显示
        total_seconds = duration_ms / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        self.total_time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # 更新播放器
        self.player_thread.set_audio(audio)
        
        # 保存设置
        self._save_settings_unique()
        
        QMessageBox.information(self, "成功", "文件加载成功！")
        
    def _save_file_unique(self):
        """保存文件"""
        if self.current_audio:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存音频文件",
                "",
                "音频文件 (*.mp3 *.wav *.ogg *.flac);;所有文件 (*.*)"
            )
            
            if file_path:
                self._start_processing_unique("export", {"filepath": file_path})
                
    def _export_file_unique(self):
        """导出文件"""
        self._save_file_unique()
        
    def _play_audio_unique(self):
        """播放音频"""
        if self.current_audio and not self.player_thread.isRunning():
            self.player_thread.start()
            self.play_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            
    def _pause_audio_unique(self):
        """暂停播放"""
        if self.player_thread.isRunning():
            if self.player_thread.is_paused:
                self.player_thread.resume()
                self.pause_button.setText("暂停")
            else:
                self.player_thread.pause()
                self.pause_button.setText("继续")
                
    def _stop_audio_unique(self):
        """停止播放"""
        self.player_thread.stop()
        self.player_thread.wait()
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText("暂停")
        self.play_progress.setValue(0)
        
    def _volume_changed_unique(self, value):
        """音量改变"""
        self.volume_label.setText(f"{value}%")
        self._save_settings_unique()
        
    def _update_play_position_unique(self, position):
        """更新播放位置"""
        if self.current_audio:
            duration = len(self.current_audio)
            self.play_progress.setMaximum(duration)
            self.play_progress.setValue(int(position))
            
            # 更新时间显示
            seconds = position / 1000
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            self.current_time_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")
            
    def _playback_finished_unique(self):
        """播放完成"""
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText("暂停")
        self.play_progress.setValue(0)
        self.current_time_label.setText("00:00:00")
        
    def _start_processing_unique(self, operation_type, extra_params=None):
        """开始处理音频"""
        if not self.current_audio:
            return
            
        # 准备参数
        params = {}
        
        if operation_type == "trim":
            params = {
                'start': self.trim_start.value(),
                'end': self.trim_end.value()
            }
        elif operation_type == "fade_in":
            params = {'duration': self.fade_in.value()}
        elif operation_type == "fade_out":
            params = {'duration': self.fade_out.value()}
        elif operation_type == "volume":
            params = {'gain': self.volume_gain.value()}
        elif operation_type == "speed":
            params = {'speed': self.speed_factor.value()}
        elif operation_type in ["highpass", "lowpass"]:
            freq = self.highpass_freq.value() if operation_type == "highpass" else self.lowpass_freq.value()
            params = {'cutoff': freq}
        elif operation_type == "export" and extra_params:
            params = extra_params
            
        # 启动处理线程
        self.processing_thread.set_operation(self.current_audio, operation_type, params)
        self.processing_started_signal.emit()
        self.processing_thread.start()
        
    @Slot()
    def _processing_started_unique(self):
        """处理开始"""
        self.global_progress.setValue(0)
        self.setEnabled(False)
        
    @Slot(object)
    def _processing_finished_unique(self, result):
        """处理完成"""
        if result:
            self.current_audio = result
            self.waveform_widget.set_audio_data(result)
            self.player_thread.set_audio(result)
            
            # 更新裁剪范围
            duration_ms = len(result)
            self.trim_start.setMaximum(duration_ms)
            self.trim_end.setMaximum(duration_ms)
            self.trim_end.setValue(duration_ms)
            
            # 更新时间显示
            total_seconds = duration_ms / 1000
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            self.total_time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
        self.processing_finished_signal.emit()
        
    @Slot()
    def _processing_finished_ui_unique(self):
        """处理完成UI更新"""
        self.setEnabled(True)
        self.global_progress.setValue(100)
        QMessageBox.information(self, "成功", "处理完成！")
        
    def _show_error_unique(self, error_message):
        """显示错误"""
        self.setEnabled(True)
        QMessageBox.critical(self, "错误", error_message)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("音频编辑器")
    app.setApplicationVersion("1.0.0")
    
    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = MainWindowUnique()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()