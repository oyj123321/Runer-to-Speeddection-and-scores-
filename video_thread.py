import cv2
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
import numpy as np
import tracker
from detector import Detector
from posture import Posture


# 创建一个自动打分的视频处理线程
class AutoScoreThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    result_folder_signal = pyqtSignal(str)

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self._is_running = True

    def run(self):
        # 调用 Posture 的 imageflow 方法
        posture = Posture()
        result_folder = posture.imageflow(self.video_path, self.change_pixmap_signal, self.progress_signal)
        
        if result_folder:
            self.result_folder_signal.emit(result_folder)
            
        self.finished_signal.emit()

    def stop(self):
        self._is_running = False
        self.wait()


# 创建一个视频处理线程
class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    progress_signal = pyqtSignal(int)

    def __init__(self, filename=None):
        super().__init__()
        self.filename = filename
        self._is_running = True
        self.tracker = tracker
        self.detector = Detector()

    def run(self):
        # 加载视频文件
        cap = cv2.VideoCapture(self.filename)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        # 创建蓝色和黄色多边形的掩码
        mask_image_temp = np.zeros((720, 1280), dtype=np.uint8)
        list_pts_blue = [[30, 474], [81, 475], [171, 430], [113, 431]]
        ndarray_pts_blue = np.array(list_pts_blue, np.int32)
        polygon_blue_value_1 = cv2.fillPoly(mask_image_temp, [ndarray_pts_blue], color=1)
        polygon_blue_value_1 = polygon_blue_value_1[:, :, np.newaxis]

        mask_image_temp = np.zeros((720, 1280), dtype=np.uint8)
        list_pts_yellow = [[1015, 475], [938, 434], [985, 433], [1087, 475]]
        ndarray_pts_yellow = np.array(list_pts_yellow, np.int32)
        polygon_yellow_value_2 = cv2.fillPoly(mask_image_temp, [ndarray_pts_yellow], color=2)
        polygon_yellow_value_2 = polygon_yellow_value_2[:, :, np.newaxis]

        # 创建结合了蓝色和黄色多边形的掩码
        polygon_mask_blue_and_yellow = polygon_blue_value_1 + polygon_yellow_value_2
        polygon_mask_blue_and_yellow = cv2.resize(polygon_mask_blue_and_yellow, (1280, 720))

        # 创建用于可视化的蓝色和黄色图像
        blue_color_plate = [255, 0, 0]
        blue_image = np.array(polygon_blue_value_1 * blue_color_plate, np.uint8)

        yellow_color_plate = [0, 255, 255]
        yellow_image = np.array(polygon_yellow_value_2 * yellow_color_plate, np.uint8)

        color_polygons_image = blue_image + yellow_image
        color_polygons_image = cv2.resize(color_polygons_image, (1280, 720))

        list_overlapping_blue_polygon = []
        list_overlapping_yellow_polygon = []

        k = 0
        count = 0
        speed = 0
        start = 0
        ending = 0
        frame_number = 0

        while True:
            frame_number += 1
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (1280, 720))

                list_bboxs = []
                bboxes = self.detector.detect(frame)

                if len(bboxes) > 0:
                    list_bboxs = self.tracker.update(bboxes, frame)
                    output_image_frame = self.tracker.draw_bboxes(frame, list_bboxs, line_thickness=None)
                else:
                    output_image_frame = frame
                output_image_frame = cv2.add(output_image_frame, color_polygons_image)

                if len(list_bboxs) > 0:
                    for item_bbox in list_bboxs:
                        x1, y1, x2, y2, label, track_id = item_bbox
                        x = x1
                        y = y2

                        # 检查对象是否与蓝色或黄色多边形重叠
                        if polygon_mask_blue_and_yellow[y, x] == 1:
                            if track_id not in list_overlapping_blue_polygon:
                                count += 1
                                list_overlapping_blue_polygon.append(track_id)
                                start = frame_number

                        elif polygon_mask_blue_and_yellow[y, x] == 2:
                            if track_id not in list_overlapping_yellow_polygon:
                                count += 1
                                ending = frame_number
                                list_overlapping_yellow_polygon.append(track_id)

                k = ending - start
                if k > 0:
                    speed = round(4.0 * fps / k, 2)
                text_draw = "Count: " + str(count) + " Speed: " + str(speed) + "m/s"
                output_image_frame = cv2.putText(img=output_image_frame, text=text_draw, org=(10, 50),
                                                 fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(255, 0, 0),
                                                 thickness=2)

                qt_img = self.convert_cv_to_qt(output_image_frame)
                self.change_pixmap_signal.emit(qt_img)

                progress = int((frame_number / frame_count) * 100)
                self.progress_signal.emit(progress)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break

        cap.release()
        cv2.destroyAllWindows()

    def convert_cv_to_qt(self, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return qt_image

    def stop(self):
        self._is_running = False
        self.wait()
