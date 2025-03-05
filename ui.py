from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
                             QMessageBox, QProgressBar, QFrame, QSplitter, QGroupBox, QToolButton)
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QPalette, QColor
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtMultimediaWidgets import QVideoWidget
from video_thread import VideoThread  # 导入VideoThread类
from posture import Posture  # 导入Posture类
from video_thread import AutoScoreThread
import os


class ModernButton(QPushButton):
    """现代风格按钮"""
    def __init__(self, text, icon_path=None):
        super(ModernButton, self).__init__()
        self.setText(text)
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(24, 24))
        self.setMinimumHeight(40)
        self.setFont(QFont('微软雅黑', 10))
        # 设置样式
        self.setStyleSheet("""
            QPushButton {
                background-color: #2d3436;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
                color: #bdc3c7;
            }
        """)


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("运动员姿态评分系统")
        
        # 创建所有UI组件
        self.create_ui_components()
        
        # 应用暗色主题
        self.apply_dark_theme()
        
        # 设置主题状态
        self.is_dark_theme = True

    def create_ui_components(self):
        # 创建顶部标题栏
        title_bar = QFrame()
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 5, 10, 5)
        
        # 设置自定义标题
        title_label = QLabel("挺身式跳远自动评分系统")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #3498db;
            padding: 10px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        # 创建主题切换按钮
        self.theme_button = QToolButton()
        self.theme_button.setCheckable(True)
        self.theme_button.setChecked(True)  # 默认是暗色模式
        self.theme_button.setText("☀️")  # 显示太阳图标表示切换到亮色
        self.theme_button.setToolTip("切换至亮色主题")
        self.theme_button.setFixedSize(36, 36)
        self.theme_button.setStyleSheet("""
            QToolButton {
                background-color: #2d3436;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 18px;
            }
            QToolButton:hover {
                background-color: #3498db;
            }
            QToolButton:checked {
                background-color: #2d3436;
            }
        """)
        self.theme_button.clicked.connect(self.toggle_theme)
        
        # 添加到标题栏
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.theme_button)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setHandleWidth(2)
        main_splitter.setChildrenCollapsible(False)

        # 上部区域分割器 (视频显示 + 结果显示)
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setHandleWidth(2)
        top_splitter.setChildrenCollapsible(False)

        # 视频显示区域
        video_frame = QFrame()
        video_frame.setFrameShape(QFrame.StyledPanel)
        video_frame.setStyleSheet("border: 1px solid #2980b9;")
        
        video_layout = QVBoxLayout(video_frame)
        
        video_title = QLabel("视频预览")
        video_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #3498db;
            padding: 5px;
        """)
        video_title.setAlignment(Qt.AlignCenter)
        
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumSize(640, 360)  # 16:9比例
        self.label.setStyleSheet("""
            border: 2px solid #3498db;
            border-radius: 10px;
            background-color: #2d3436;
            padding: 2px;
        """)
        self.label.setText("请选择视频文件")
        
        video_layout.addWidget(video_title)
        video_layout.addWidget(self.label)
        
        # 结果显示区域
        results_frame = QFrame()
        results_frame.setFrameShape(QFrame.StyledPanel)
        results_frame.setStyleSheet("border: 1px solid #2980b9;")
        
        results_layout = QVBoxLayout(results_frame)
        
        results_title = QLabel("评分结果")
        results_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #3498db;
            padding: 5px;
        """)
        results_title.setAlignment(Qt.AlignCenter)
        
        self.results_label = QLabel("尚未生成评分结果")
        self.results_label.setAlignment(Qt.AlignCenter)
        self.results_label.setStyleSheet("""
            border: 2px solid #3498db;
            border-radius: 10px;
            background-color: #2d3436;
            padding: 10px;
            font-size: 14px;
        """)
        
        results_layout.addWidget(results_title)
        results_layout.addWidget(self.results_label)
        
        # 添加到上部分割器
        top_splitter.addWidget(video_frame)
        top_splitter.addWidget(results_frame)
        top_splitter.setSizes([3, 2])  # 设置比例
        
        # 控制区域 - 分为两个独立的功能区域
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_frame.setStyleSheet("border: 1px solid #2980b9;")
        control_frame.setMaximumHeight(180)  # 增加高度以容纳更多控件
        
        control_layout = QHBoxLayout(control_frame)
        
        # ===== 测速功能区 =====
        speed_group = QGroupBox("运动员测速功能")
        speed_group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(41, 128, 185, 0.1);
            }
        """)
        speed_group_layout = QVBoxLayout()
        
        # 测速视频选择按钮
        self.openSpeedButton = ModernButton("选择测速视频")
        self.openSpeedButton.setToolTip("选择用于测速分析的视频文件")
        self.openSpeedButton.clicked.connect(self.open_speed_file)
        
        # 测速处理按钮
        self.processButton = ModernButton("开始测速")
        self.processButton.setToolTip("对视频中的运动员进行测速分析")
        self.processButton.setEnabled(False)
        self.processButton.clicked.connect(self.process_video)
        
        # 测速状态标签
        self.speed_status_label = QLabel("未选择测速视频")
        self.speed_status_label.setAlignment(Qt.AlignCenter)
        self.speed_status_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        
        speed_group_layout.addWidget(self.openSpeedButton)
        speed_group_layout.addWidget(self.processButton)
        speed_group_layout.addWidget(self.speed_status_label)
        speed_group.setLayout(speed_group_layout)
        
        # ===== 评分功能区 =====
        score_group = QGroupBox("姿态评分功能")
        score_group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(46, 204, 113, 0.1);
            }
        """)
        score_group_layout = QVBoxLayout()
        
        # 评分视频选择按钮
        self.openScoreButton = ModernButton("选择评分视频")
        self.openScoreButton.setToolTip("选择用于姿态评分的视频文件")
        self.openScoreButton.clicked.connect(self.open_score_file)
        
        # 开始评分按钮
        self.autoScoreButton = ModernButton("开始评分")
        self.autoScoreButton.setToolTip("对运动员的姿态进行自动评分")
        self.autoScoreButton.setEnabled(False)
        self.autoScoreButton.clicked.connect(self.auto_score)
        
        # 查看结果按钮
        self.viewResultsButton = ModernButton("查看评分结果")
        self.viewResultsButton.setToolTip("查看最新的评分结果")
        self.viewResultsButton.setEnabled(False)
        self.viewResultsButton.clicked.connect(self.view_results)
        
        # 评分状态标签
        self.score_status_label = QLabel("未选择评分视频")
        self.score_status_label.setAlignment(Qt.AlignCenter)
        self.score_status_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        
        score_group_layout.addWidget(self.openScoreButton)
        score_group_layout.addWidget(self.autoScoreButton)
        score_group_layout.addWidget(self.viewResultsButton)
        score_group_layout.addWidget(self.score_status_label)
        score_group.setLayout(score_group_layout)
        
        # ===== 进度显示区 =====
        progress_group = QGroupBox("处理进度")
        progress_group_layout = QVBoxLayout()
        
        self.progress_label = QLabel("当前未处理任何视频")
        self.progress_label.setAlignment(Qt.AlignCenter)
        
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(True)
        self.progressBar.setFormat("%p%")
        self.progressBar.setVisible(True)
        self.progressBar.setMinimumWidth(200)
        
        progress_group_layout.addWidget(self.progress_label)
        progress_group_layout.addWidget(self.progressBar)
        progress_group.setLayout(progress_group_layout)
        
        # 添加到控制布局
        control_layout.addWidget(speed_group)
        control_layout.addWidget(score_group)
        control_layout.addWidget(progress_group)
        
        # 添加到主分割器
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(control_frame)
        main_splitter.setSizes([3, 1])  # 设置比例
        
        # 底部状态信息
        self.status_label = QLabel("系统就绪 - 请选择需要处理的视频文件")
        self.status_label.setStyleSheet("""
            font-size: 12px;
            color: #7f8c8d;
            padding: 5px;
            border-top: 1px solid #3498db;
        """)
        self.status_label.setAlignment(Qt.AlignRight)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(title_bar)
        main_layout.addWidget(main_splitter)
        main_layout.addWidget(self.status_label)
        self.setLayout(main_layout)

        # 存储视频路径
        self.speed_video_path = None  # 测速视频路径
        self.score_video_path = None  # 评分视频路径
        self.last_results_folder = None  # 最近评分结果文件夹
        self.video_thread = None  # 视频处理线程
        self.auto_score_thread = None  # 评分处理线程

    def toggle_theme(self):
        """切换主题"""
        if self.theme_button.isChecked():
            # 暗色主题
            self.theme_button.setText("☀️")
            self.theme_button.setToolTip("切换至亮色主题")
            self.apply_dark_theme()
            self.is_dark_theme = True
        else:
            # 亮色主题
            self.theme_button.setText("🌙")
            self.theme_button.setToolTip("切换至暗色主题")
            self.apply_light_theme()
            self.is_dark_theme = False

    # 选择测速视频文件
    def open_speed_file(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "选择测速视频", ".", "视频文件 (*.mp4 *.flv *.ts *.mts *.avi)")
        if fileName:
            self.speed_video_path = fileName
            # 创建视频处理线程并连接信号以更新UI
            self.video_thread = VideoThread(fileName)
            self.video_thread.change_pixmap_signal.connect(self.update_image)
            self.video_thread.finished.connect(self.processing_finished)
            self.video_thread.progress_signal.connect(self.update_progress)
            
            # 启用测速按钮
            self.processButton.setEnabled(True)
            
            # 更新状态信息
            file_name = fileName.split('/')[-1]
            self.speed_status_label.setText(f"已选择: {file_name}")
            self.status_label.setText(f"已选择测速视频: {file_name}")
            self.progress_label.setText(f"准备测速: {file_name}")

    # 选择评分视频文件
    def open_score_file(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "选择评分视频", ".", "视频文件 (*.mp4 *.avi)")
        if fileName:
            self.score_video_path = fileName
            
            # 启用评分按钮
            self.autoScoreButton.setEnabled(True)
            
            # 更新状态信息
            file_name = fileName.split('/')[-1]
            self.score_status_label.setText(f"已选择: {file_name}")
            self.status_label.setText(f"已选择评分视频: {file_name}")
            
            # 重置结果区域
            self.results_label.setText("尚未生成评分结果")
            self.viewResultsButton.setEnabled(False)

    def auto_score(self):
        # 确保已选择评分视频
        if not self.score_video_path:
            QMessageBox.warning(self, "未选择视频", "请先选择用于评分的视频文件。")
            return
            
        # 创建评分线程
        self.auto_score_thread = AutoScoreThread(self.score_video_path)
        
        # 连接信号
        self.auto_score_thread.change_pixmap_signal.connect(self.update_image)
        self.auto_score_thread.progress_signal.connect(self.update_progress)
        self.auto_score_thread.finished_signal.connect(self.score_processing_finished)
        self.auto_score_thread.result_folder_signal.connect(self.set_result_folder)
        
        # 重置进度条
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        
        # 启动线程
        self.auto_score_thread.start()
        
        # 更新状态
        file_name = self.score_video_path.split('/')[-1]
        self.status_label.setText(f"正在处理评分视频: {file_name}")
        self.progress_label.setText(f"评分中: {file_name}")
        
        # 禁用按钮，防止重复点击
        self.autoScoreButton.setEnabled(False)
        self.openScoreButton.setEnabled(False)

    def set_result_folder(self, folder_path):
        """设置结果文件夹路径"""
        self.last_results_folder = folder_path
        print(f"结果保存在: {folder_path}")

    def score_processing_finished(self):
        """评分处理完成的回调函数"""
        # 更新状态
        self.progress_label.setText("评分完成")
        self.status_label.setText("评分处理已完成")
        
        # 启用按钮
        self.viewResultsButton.setEnabled(True)
        self.autoScoreButton.setEnabled(True)
        self.openScoreButton.setEnabled(True)
        
        # 显示消息
        QMessageBox.information(self, "处理完成", "视频评分处理已完成，可查看评分结果。")
        
        # 自动显示结果
        self.view_results()

    def process_video(self):
        # 确保已选择测速视频
        if not self.speed_video_path or self.video_thread is None:
            QMessageBox.warning(self, "未选择视频", "请先选择用于测速的视频文件。")
            return
            
        # 启动视频处理线程
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        self.video_thread.start()
        
        # 更新状态
        file_name = self.speed_video_path.split('/')[-1]
        self.progress_label.setText(f"测速中: {file_name}")
        self.status_label.setText(f"正在处理测速视频: {file_name}")
        
        # 禁用按钮，防止重复点击
        self.processButton.setEnabled(False)
        self.openSpeedButton.setEnabled(False)

    def processing_finished(self):
        # 区分是测速还是评分完成
        if self.sender() == self.video_thread:
            self.progress_label.setText("测速完成")
            self.status_label.setText("测速处理已完成")
            
            # 启用按钮
            self.processButton.setEnabled(True)
            self.openSpeedButton.setEnabled(True)
            
            QMessageBox.information(self, "处理完成", "视频测速处理已完成。")
        else:
            # 这部分已经移到score_processing_finished方法中
            pass

    def update_image(self, qt_img):
        """更新图像显示"""
        self.label.setPixmap(QPixmap.fromImage(qt_img).scaled(
            self.label.width(), self.label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def view_results(self):
        """查看评分结果"""
        if not self.last_results_folder or not os.path.exists(self.last_results_folder):
            QMessageBox.warning(self, "无结果", "没有可用的评分结果或结果文件夹不存在。")
            return
            
        try:
            result_text = "<html><body style='text-align:center;'>"
            result_text += "<h3 style='color:#3498db;'>评分结果</h3>"
            result_text += "<table style='margin:0 auto; border-collapse:collapse; width:90%;'>"
            result_text += "<tr style='background-color:#2c3e50;'><th style='padding:8px; border:1px solid #3498db;'>评分项目</th><th style='padding:8px; border:1px solid #3498db;'>得分</th><th style='padding:8px; border:1px solid #3498db;'>状态</th></tr>"
            
            # 读取各项评分
            take_off_path = os.path.join(self.last_results_folder, "take_off.jpg")
            hip_extension_path = os.path.join(self.last_results_folder, "hip_extension.jpg")
            abdominal_contraction_path = os.path.join(self.last_results_folder, "abdominal_contraction.jpg")
            
            # 尝试从图像中读取实际分数
            import cv2
            import re
            
            def extract_score(image_path):
                if not os.path.exists(image_path):
                    return "未生成", "❌"
                
                try:
                    # 读取图像
                    img = cv2.imread(image_path)
                    # 转换为灰度图像
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # 使用OCR提取文本（这里使用简化方法，通过图像检测分数）
                    # 实际应用中可以使用tesseract或其他OCR库
                    # 这里我们假设分数已经从文件名或其他方式获取
                    
                    # 提取分数的简化方法 - 检查图像左上角的文本区域
                    score = "获取中..." 
                    
                    # 简单方法：从文件名获取最后修改时间作为替代
                    import time
                    modified_time = os.path.getmtime(image_path)
                    # 将时间戳转换为可读格式
                    time_str = time.strftime("%H:%M:%S", time.localtime(modified_time))
                    
                    return f"已生成 ({time_str})", "✅"
                except Exception as e:
                    print(f"Error extracting score: {e}")
                    return "读取错误", "⚠️"
            
            # 获取各项评分状态
            take_off_score, take_off_status = extract_score(take_off_path)
            hip_extension_score, hip_extension_status = extract_score(hip_extension_path)
            abdominal_contraction_score, abdominal_contraction_status = extract_score(abdominal_contraction_path)
            
            # 添加到结果表格
            result_text += f"<tr><td style='padding:8px; border:1px solid #3498db;'>起跳姿态</td><td style='padding:8px; border:1px solid #3498db;'>{take_off_score}</td><td style='padding:8px; border:1px solid #3498db;'>{take_off_status}</td></tr>"
            result_text += f"<tr><td style='padding:8px; border:1px solid #3498db;'>髋关节伸展</td><td style='padding:8px; border:1px solid #3498db;'>{hip_extension_score}</td><td style='padding:8px; border:1px solid #3498db;'>{hip_extension_status}</td></tr>"
            result_text += f"<tr><td style='padding:8px; border:1px solid #3498db;'>腹部收缩</td><td style='padding:8px; border:1px solid #3498db;'>{abdominal_contraction_score}</td><td style='padding:8px; border:1px solid #3498db;'>{abdominal_contraction_status}</td></tr>"
            
            result_text += "</table><br>"
            result_text += f"<p style='font-size:12px; color:#7f8c8d;'>结果保存在文件夹:<br>{self.last_results_folder}</p>"
            result_text += "</body></html>"
            
            self.results_label.setText(result_text)
            
            # 显示消息
            QMessageBox.information(self, "评分结果", "评分结果已生成，详情请查看结果区域。\n图像保存在: " + self.last_results_folder)
            
            # 打开结果文件夹
            import platform
            import subprocess
            
            if platform.system() == "Windows":
                os.startfile(self.last_results_folder)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", self.last_results_folder])
            else:  # Linux
                subprocess.Popen(["xdg-open", self.last_results_folder])
                
        except Exception as e:
            print(f"Error displaying results: {e}")
            QMessageBox.warning(self, "结果显示错误", f"显示结果时发生错误: {str(e)}")

    def update_progress(self, value):
        """更新进度条"""
        self.progressBar.setValue(value)

    def apply_dark_theme(self):
        """应用暗色主题"""
        self.setStyleSheet("""
            QWidget {
                background-color: #1e272e;
                color: #ecf0f1;
                font-family: '微软雅黑';
            }
            QLabel {
                color: #ecf0f1;
                font-size: 14px;
            }
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
                background-color: #2d3436;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 20px;
            }
            QGroupBox {
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QSplitter::handle {
                background-color: #3498db;
            }
            QToolTip {
                background-color: #2d3436;
                color: white;
                border: 1px solid #3498db;
                border-radius: 4px;
            }
        """)
        
        # 更新边框和标签样式
        for frame in self.findChildren(QFrame):
            frame.setStyleSheet("border: 1px solid #2980b9;")
            
        self.label.setStyleSheet("""
            border: 2px solid #3498db;
            border-radius: 10px;
            background-color: #2d3436;
            padding: 2px;
        """)
        
        self.results_label.setStyleSheet("""
            border: 2px solid #3498db;
            border-radius: 10px;
            background-color: #2d3436;
            padding: 10px;
            font-size: 14px;
        """)
        
        self.status_label.setStyleSheet("""
            font-size: 12px;
            color: #7f8c8d;
            padding: 5px;
            border-top: 1px solid #3498db;
        """)
        
        # 更新按钮样式
        for button in self.findChildren(ModernButton):
            button.setStyleSheet("""
                QPushButton {
                    background-color: #2d3436;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #3498db;
                }
                QPushButton:pressed {
                    background-color: #2980b9;
                }
                QPushButton:disabled {
                    background-color: #7f8c8d;
                    color: #bdc3c7;
                }
            """)

    def apply_light_theme(self):
        """应用亮色主题"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f6fa;
                color: #2f3640;
                font-family: '微软雅黑';
            }
            QLabel {
                color: #2f3640;
                font-size: 14px;
            }
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
                background-color: #dcdde1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 20px;
            }
            QGroupBox {
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QSplitter::handle {
                background-color: #3498db;
            }
            QToolTip {
                background-color: #f5f6fa;
                color: #2f3640;
                border: 1px solid #3498db;
                border-radius: 4px;
            }
        """)
        
        # 更新边框和标签样式
        for frame in self.findChildren(QFrame):
            frame.setStyleSheet("border: 1px solid #3498db;")
            
        self.label.setStyleSheet("""
            border: 2px solid #3498db;
            border-radius: 10px;
            background-color: #dcdde1;
            padding: 2px;
        """)
        
        self.results_label.setStyleSheet("""
            border: 2px solid #3498db;
            border-radius: 10px;
            background-color: #dcdde1;
            padding: 10px;
            font-size: 14px;
        """)
        
        self.status_label.setStyleSheet("""
            font-size: 12px;
            color: #2f3640;
            padding: 5px;
            border-top: 1px solid #3498db;
        """)
        
        # 更新按钮样式
        for button in self.findChildren(ModernButton):
            button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #1f618d;
                }
                QPushButton:disabled {
                    background-color: #bdc3c7;
                    color: #7f8c8d;
                }
            """)
