import glob
from tkinter import filedialog
import mediapipe as mp
import cv2
import os
import math
import numpy as np
from PyQt5.QtGui import QImage
from joblib import load
import pandas as pd
import re


def back_to_origin(points, image_shape):
    origin_points = []
    height, width, _ = image_shape
    for point in points:
        origin_points.append([point[0] * width, point[1] * height])
    return origin_points


def read_points_from_file(filename):
    filename = os.path.join('./', filename)
    points = []
    with open(filename, 'r') as file:
        for line in file:
            x, y = line.strip().split(',')
            points.append((float(x), float(y)))
    return points


def get_Scoring(model_str, angles):
    model_name = model_str + ".joblib"
    data = np.array(angles).reshape(1, -1)
    model = load(model_name)
    score = model.predict(data)
    return score


def calculate_angle(A, B, C):
    """计算两个向量之间的夹角

    Args:
        A (_type_): point A
        B (_type_): point B
        C (_type_): point C

    Returns:
        _type_: angle between AB and BC
    """
    AB = (B[0] - A[0], B[1] - A[1])
    BC = (C[0] - B[0], C[1] - B[1])

    dot_product = AB[0] * BC[0] + AB[1] * BC[1]

    length_AB = math.sqrt(AB[0] ** 2 + AB[1] ** 2)
    length_BC = math.sqrt(BC[0] ** 2 + BC[1] ** 2)

    angle_radians = math.acos(dot_product / (length_AB * length_BC))
    angle_degrees = math.degrees(angle_radians)

    # 检查角度是否接近于零
    if abs(angle_degrees) < 1e-6:
        angle_degrees = 0.0

    return angle_degrees


# 新增 - 计算腾起角的函数
def calculate_take_off_angle(anchor_x, anchor_y, cg_x, cg_y):
    dx = cg_x - anchor_x
    dy = anchor_y - cg_y  # 更改为 anchor_y - cg_y 因为图像坐标系中，Y方向是向下的
    angle = math.atan2(dy, dx) * 180 / math.pi
    return angle


def calculate_take_off_angles(points):
    # 切记用归一化的角来计算
    angles = []
    theta1 = calculate_angle(points[9], points[11], points[3])
    angles.append(theta1)
    temp_point = (points[10][0] + 1, points[10][1])
    theta2 = calculate_angle(points[12], points[10], temp_point)
    angles.append(theta2)
    theta3 = calculate_angle(points[10], points[12], points[14])
    angles.append(theta3)
    return angles


def calculate_distance(test_points, posture_type, weights, threshold):
    # 权重自设
    if posture_type and posture_type != '':
        filename = posture_type + '.txt'
        standard_points = read_points_from_file(filename)
        p = calculate_take_off_angles(test_points)  # 测试姿态角向量合集
        q = calculate_take_off_angles(standard_points)  # 标准姿态角向量合集

        # 计算加权余弦距离
        d = math.sqrt(sum((x - y) ** 2 * w for x, y, w in zip(p, q, weights)))

        if d < threshold:
            dot_product = np.dot(p, q)
            magnitude_p = np.linalg.norm(p)
            magnitude_q = np.linalg.norm(q)

            cosine_distance = dot_product / (magnitude_p * magnitude_q)
            d_cos = 1 - cosine_distance

            d = 0.7 * d + 0.3 * d_cos

        return d, p


def plot_construct_point(image, points, color=(0, 0, 255)):
    if points != []:
        image = np.ascontiguousarray(np.copy(image))
        """将点数组画成人体结构

        Args:
            image (_type_): _description_
            points (_type_): _description_
            color (tuple, optional): _description_. Defaults to (0, 0, 255).

        Returns:
            image: _description_
        """
        points = [(int(x), int(y)) for x, y in points]

        # 画头,脖子，髋
        cv2.line(image, points[0], points[1], color, 2, cv2.LINE_AA)
        cv2.line(image, points[1], points[2], color, 2, cv2.LINE_AA)

        # 画骨架
        skeleton_points = [points[3], points[4], points[10], points[9]]
        cv2.polylines(image, [np.array(skeleton_points)], isClosed=True, color=color, thickness=2)

        # 画手臂
        cv2.line(image, points[3], points[5], color, 2, cv2.LINE_AA)
        cv2.line(image, points[5], points[7], color, 2, cv2.LINE_AA)
        cv2.line(image, points[4], points[6], color, 2, cv2.LINE_AA)
        cv2.line(image, points[6], points[8], color, 2, cv2.LINE_AA)

        # 画腿
        cv2.line(image, points[9], points[11], color, 2, cv2.LINE_AA)
        cv2.line(image, points[11], points[13], color, 2, cv2.LINE_AA)
        cv2.line(image, points[10], points[12], color, 2, cv2.LINE_AA)
        cv2.line(image, points[12], points[14], color, 2, cv2.LINE_AA)

        # 画脚
        left_foot_points = [points[13], points[15], points[17]]
        right_foot_points = [points[14], points[16], points[18]]
        cv2.polylines(image, [np.array(left_foot_points)], isClosed=True, color=color, thickness=2)
        cv2.polylines(image, [np.array(right_foot_points)], isClosed=True, color=color, thickness=2)

        # 画点
        for i, point in enumerate(points):
            cv2.circle(image, point, 1, (255, 0, 0), 2)
            cv2.putText(image, str(i), (point[0] + 5, point[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1,
                        cv2.LINE_AA)

    return image


def construct_point(landmarks):
    """按照挺身式跳远重构关键点

    Args:
        landmarks (_type_): _description_

    Returns:
        points: 重构后的关键点
    """
    construct_num = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
    points = []
    i = 0

    # 取鼻子,肩中点和髋中点
    nose = [(landmarks[0].x), (landmarks[0].y)]
    points.append(nose)

    shoulder_mid = [((landmarks[11].x + landmarks[12].x) / 2), ((landmarks[11].y + landmarks[12].y) / 2)]
    points.append(shoulder_mid)

    hip_mid = [((landmarks[23].x + landmarks[24].x) / 2), ((landmarks[23].y + landmarks[24].y) / 2)]
    points.append(hip_mid)

    while i < len(construct_num):
        points.append([landmarks[construct_num[i]].x, landmarks[construct_num[i]].y])
        i = i + 1

    return points


def select_video():
    video_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4;*.avi")])
    if video_path:
        print("Selected video:", video_path)
        return video_path

    else:
        print("No video selected.")


class Posture(object):
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.min_dconf = 0.5
        self.min_tconf = 0.5
        self.weight = [0.3, 0.5, 0.2]
        self.threshold = 1

    def imageflow(self, video_path, change_pixmap_signal, progress_signal=None):
        cap = cv2.VideoCapture(video_path)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)  # float
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # 获取总帧数

        file = video_path.split("/")[-1]
        if "\\" in video_path:
            file = video_path.split("\\")[-1]
        file_name = file.split(".")[0]
        file_type = "." + file.split(".")[1]
        
        # 在当前工作目录下创建结果文件夹，避免中文路径问题
        output_dir = os.getcwd()  # 获取当前工作目录
        
        # 确保文件名不包含可能导致问题的字符
        safe_file_name = re.sub(r'[^\w\-_]', '_', file_name)
        
        save_folder = os.path.join(output_dir, safe_file_name)
        os.makedirs(save_folder, exist_ok=True)
        save_path = os.path.join(save_folder, safe_file_name + "_jump" + file_type)

        vid_writer = cv2.VideoWriter(
            save_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (int(width), int(height))
        )

        pose = self.mp_pose.Pose(min_detection_confidence=self.min_dconf, min_tracking_confidence=self.min_tconf)
        frame_id = 0
        flag = True
        image = None
        d_take_off = {'d': 1000., 'points': [], 'frame_id': [], 'angles': [], 'score': []}
        d_hip_extension = {'d': 1000., 'points': [], 'frame_id': [], 'angles': [], 'score': []}
        d_abdominal_contraction = {'d': 1000., 'points': [], 'frame_id': [], 'angles': [], 'score': []}

        while flag:
            ret_val, frame = cap.read()
            if ret_val:
                results = pose.process(frame)
                normalized_points = []
                origin_points = []

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    normalized_points = construct_point(landmarks)

                    # 计算是否抵达待测姿态
                    temp1, angles1 = calculate_distance(normalized_points, 'take_off', self.weight, self.threshold)
                    temp2, angles2 = calculate_distance(normalized_points, 'hip_extension', self.weight, self.threshold)
                    temp3, angles3 = calculate_distance(normalized_points, 'abdominal_contraction', self.weight,
                                                        self.threshold)

                    if d_take_off['d'] is not None and temp1 is not None:
                        if d_take_off['d'] > temp1:
                            d_take_off['d'] = temp1
                            d_take_off['points'] = normalized_points
                            d_take_off['frame_id'] = frame_id
                            d_take_off['angles'] = angles1

                    # 计算 'hip_extension'
                    if d_hip_extension['d'] is not None and temp2 is not None:
                        if d_hip_extension['d'] > temp2:
                            d_hip_extension['d'] = temp2
                            d_hip_extension['points'] = normalized_points
                            d_hip_extension['frame_id'] = frame_id
                            d_hip_extension['angles'] = angles2

                    # 计算 'abdominal_contraction'
                    if d_abdominal_contraction['d'] is not None and temp3 is not None:
                        if d_abdominal_contraction['d'] > temp3:
                            d_abdominal_contraction['d'] = temp3
                            d_abdominal_contraction['points'] = normalized_points
                            d_abdominal_contraction['frame_id'] = frame_id
                            d_abdominal_contraction['angles'] = angles3

                    if image is not None:
                        origin_points = back_to_origin(normalized_points, image.shape)

                    # 新增 - 计算起跳角度并显示在视频上
                    anchor = results.pose_landmarks.landmark[13]  # 左脚踝为参考点
                    anchor_x, anchor_y = anchor.x, anchor.y
                    cg = results.pose_landmarks.landmark[9]  # 左髋关节为重心点
                    cg_x, cg_y = cg.x, cg.y
                    angle = calculate_take_off_angle(anchor_x, anchor_y, cg_x, cg_y)
                    angle_text = f'Take off angle: {angle:.2f} degrees'
                    cv2.putText(frame, angle_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

                image = plot_construct_point(frame, points=origin_points)

                #cv2.imshow('result', image)
                vid_writer.write(image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                break
            
            # 更新进度
            frame_id += 1
            if progress_signal and total_frames > 0:
                progress = int((frame_id / total_frames) * 100)
                progress_signal.emit(progress)

            # 将 OpenCV 图像转换为 QImage
            qt_img = self.convert_cv_to_qt(frame)
            change_pixmap_signal.emit(qt_img)

        cap.release()
        cv2.destroyAllWindows()

        width, height = 1280, 720
        canvas = cv2.cvtColor(np.ones((height, width, 3), dtype=np.uint8) * 255, cv2.COLOR_BGR2RGB)  # 创建白色背景画布
        d_take_off["score"] = get_Scoring("take_off", d_take_off["angles"])
        d_hip_extension["score"] = get_Scoring("hip_extension", d_hip_extension["angles"])
        d_abdominal_contraction["score"] = get_Scoring("abdominal_contraction", d_abdominal_contraction["angles"])

        # 创建 'take_off' 图像，将 'take_off' 关键点绘制在画布上，并保存为 'take_off.jpg'
        take_off_points = back_to_origin(d_take_off['points'], canvas.shape)
        canvas_take_off = plot_construct_point(canvas, take_off_points, color=(0, 255, 0))
        # 在左上角写入分数
        cv2.putText(canvas_take_off, f'Score: {d_take_off["score"]}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 0, 0), 2, cv2.LINE_AA)
        cv2.imwrite(os.path.join(save_folder, "take_off.jpg"), canvas_take_off)

        # 创建 'hip_extension' 图像，将 'hip_extension' 关键点绘制在画布上，并保存为 'hip_extension.jpg'
        hip_extension_points = back_to_origin(d_hip_extension['points'], canvas.shape)
        canvas_hip_extension = plot_construct_point(canvas, hip_extension_points, color=(255, 0, 0))
        # 在左上角写入分数
        cv2.putText(canvas_hip_extension, f'Score: {d_hip_extension["score"]}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 0, 0), 2, cv2.LINE_AA)
        cv2.imwrite(os.path.join(save_folder, "hip_extension.jpg"), canvas_hip_extension)

        # 创建 'abdominal_contraction' 图像，将 'abdominal_contraction' 关键点绘制在画布上，并保存为 'abdominal_contraction.jpg'
        abdominal_contraction_points = back_to_origin(d_abdominal_contraction['points'], canvas.shape)
        canvas_abdominal_contraction = plot_construct_point(canvas, abdominal_contraction_points, color=(0, 0, 255))
        # 在左上角写入分数
        cv2.putText(canvas_abdominal_contraction, f'Score: {d_abdominal_contraction["score"]}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.imwrite(os.path.join(save_folder, "abdominal_contraction.jpg"), canvas_abdominal_contraction)
        
        # 返回结果文件夹路径
        return save_folder

    def convert_cv_to_qt(self, frame):
        """将 OpenCV 图像转换为 QImage"""
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # 将 BGR 转换为 RGB
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return qt_image


def process_video_folder(folder_path):
    video_files = get_video_files(folder_path)
    posture = Posture()

    for video_path in video_files:
        print("Processing video:", video_path)
        posture.imageflow(video_path)


def get_video_files(folder_path):
    video_files = []
    file_patterns = ['*.mp4', '*.avi']  # 可以根据需要添加更多的视频文件扩展名
    for pattern in file_patterns:
        folder_pattern = os.path.join(folder_path, pattern)
        files = glob.glob(folder_pattern)
        # 替换路径中的反斜杠为斜杠
        # files = [file.replace("\\", "/") for file in files]
        video_files.extend(files)

    # 提取文件名中的数字并按数字大小进行排序
    video_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))

    return video_files
