from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
                             QMessageBox, QProgressBar)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtMultimediaWidgets import QVideoWidget
from video_thread import VideoThread  # 导入VideoThread类
from posture import Posture  # 导入Posture类
from video_thread import AutoScoreThread


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("挺身式跳远自动评分系统")

        self.videoWidget = QVideoWidget()
        video_layout = QHBoxLayout()
        video_layout.addWidget(self.videoWidget)

        self.label = QLabel()
        self.label.setFixedSize(1280, 720)
        video_layout.addWidget(self.label)

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setVisible(False)

        # 创建视频播放区域布局
        control_layout = QVBoxLayout()

        self.openButton = QPushButton("读取视频")
        self.openButton.clicked.connect(self.open_file)

        self.processButton = QPushButton("人员测速")
        # self.processButton.setFixedSize(100, 30)  # 设置按钮大小
        self.processButton.setEnabled(False)
        self.processButton.clicked.connect(self.process_video)

        self.autoScoreButton = QPushButton("自动打分")
        self.autoScoreButton.setEnabled(False)
        self.autoScoreButton.clicked.connect(self.auto_score)

        control_layout.addWidget(self.openButton)
        control_layout.addWidget(self.processButton)
        control_layout.addWidget(self.autoScoreButton)
        control_layout.addWidget(self.progressBar)

        main_layout = QVBoxLayout()
        main_layout.addLayout(video_layout)
        main_layout.addLayout(control_layout)
        self.setLayout(main_layout)

        self.video_thread = None

    def open_file(self):
        # 打开文件对话框选择视频文件
        fileName, _ = QFileDialog.getOpenFileName(self, "打开视频", ".", "视频文件 (*.mp4 *.flv *.ts *.mts *.avi)")
        if fileName:
            # 创建视频处理线程并连接信号以更新UI
            self.video_thread = VideoThread(fileName)
            self.video_thread.change_pixmap_signal.connect(self.update_image)
            self.video_thread.finished.connect(self.processing_finished)
            self.video_thread.progress_signal.connect(self.update_progress)
            self.processButton.setEnabled(True)  # 启用测速按钮
            self.autoScoreButton.setEnabled(True)  # 启用自动打分按钮

    def auto_score(self):
        # 选择视频文件
        video_path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi)")
        if video_path:
            self.auto_score_thread = AutoScoreThread(video_path)
            self.auto_score_thread.change_pixmap_signal.connect(self.update_image)
            self.auto_score_thread.start()

    def update_image(self, qt_img):
        # 使用处理后的帧图像更新标签
        self.label.setPixmap(QPixmap.fromImage(qt_img))

    def process_video(self):
        # 启动视频处理线程
        if self.video_thread is not None:
            self.progressBar.setValue(0)
            self.progressBar.setVisible(True)
            self.video_thread.start()

    def update_image(self, qt_img):
        # 使用处理后的帧图像更新标签
        self.label.setPixmap(QPixmap.fromImage(qt_img))

    def update_progress(self, value):
        # 更新进度条
        self.progressBar.setValue(value)

    def processing_finished(self):
        # 视频处理完成时显示消息框
        self.progressBar.setVisible(False)
        QMessageBox.information(self, "处理完成", "视频处理已完成。")
