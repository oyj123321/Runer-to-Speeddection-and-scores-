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
        self.speed = 0.0  # 添加速度属性
        # 性能优化参数
        self.frame_skip = 1  # 降低到每1帧处理一次，确保不遗漏关键帧
        self.process_width = 960  # 提高处理分辨率为原来的75%
        self.process_height = 540  # 提高处理分辨率为原来的75% 
        self.display_width = 1280  # 显示分辨率宽度
        self.display_height = 720  # 显示分辨率高度
        self.early_stop_threshold = 0.8  # 提高到80%，确保不会错过重要帧
        self.overlap_margin = 5  # 添加重叠检测的边界容差
        self.speed_calculated = False  # 新增标志，表示是否已完成测速

    def run(self):
        # 加载视频文件
        cap = cv2.VideoCapture(self.filename)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        # 缩放多边形区域到处理分辨率
        scale_x = self.process_width / 1280.0
        scale_y = self.process_height / 720.0
        
        # 创建蓝色和黄色多边形的掩码 - 缩放到处理分辨率
        mask_image_temp = np.zeros((self.process_height, self.process_width), dtype=np.uint8)
        list_pts_blue = [[int(30*scale_x), int(474*scale_y)], 
                         [int(81*scale_x), int(475*scale_y)], 
                         [int(171*scale_x), int(430*scale_y)], 
                         [int(113*scale_x), int(431*scale_y)]]
        ndarray_pts_blue = np.array(list_pts_blue, np.int32)
        polygon_blue_value_1 = cv2.fillPoly(mask_image_temp, [ndarray_pts_blue], color=1)
        polygon_blue_value_1 = polygon_blue_value_1[:, :, np.newaxis]

        mask_image_temp = np.zeros((self.process_height, self.process_width), dtype=np.uint8)
        list_pts_yellow = [[int(1015*scale_x), int(475*scale_y)], 
                          [int(938*scale_x), int(434*scale_y)], 
                          [int(985*scale_x), int(433*scale_y)], 
                          [int(1087*scale_x), int(475*scale_y)]]
        ndarray_pts_yellow = np.array(list_pts_yellow, np.int32)
        polygon_yellow_value_2 = cv2.fillPoly(mask_image_temp, [ndarray_pts_yellow], color=2)
        polygon_yellow_value_2 = polygon_yellow_value_2[:, :, np.newaxis]

        # 创建结合了蓝色和黄色多边形的掩码
        polygon_mask_blue_and_yellow = polygon_blue_value_1 + polygon_yellow_value_2

        # 创建用于可视化的蓝色和黄色图像
        blue_color_plate = [255, 0, 0]
        blue_image = np.array(polygon_blue_value_1 * blue_color_plate, np.uint8)

        yellow_color_plate = [0, 255, 255]
        yellow_image = np.array(polygon_yellow_value_2 * yellow_color_plate, np.uint8)

        color_polygons_image = blue_image + yellow_image

        list_overlapping_blue_polygon = []
        list_overlapping_yellow_polygon = []

        k = 0
        count = 0
        speed = 0
        start = 0
        ending = 0
        frame_number = 0
        processed_frames = 0
        last_display_frame = None

        while True and self._is_running:
            frame_number += 1
            ret, frame = cap.read()
            if ret:
                # 跳帧处理
                if frame_number % self.frame_skip != 0:
                    # 更新进度条但不处理
                    progress = int((frame_number / frame_count) * 100)
                    self.progress_signal.emit(progress)
                    
                    # 检查是否已经有测速结果且已经处理了足够多的帧
                    if speed > 0 and frame_number > frame_count * self.early_stop_threshold:
                        # 已经有测速结果并且处理帧数超过阈值，可以提前结束
                        break
                    
                    continue
                
                processed_frames += 1
                
                # 降低处理分辨率
                small_frame = cv2.resize(frame, (self.process_width, self.process_height))
                
                # 保留原始帧用于显示
                display_frame = cv2.resize(frame, (self.display_width, self.display_height))
                last_display_frame = display_frame.copy()

                list_bboxs = []
                # 在降低分辨率的帧上进行检测
                bboxes = self.detector.detect(small_frame)

                if len(bboxes) > 0:
                    # 在小尺寸帧上更新跟踪器
                    list_bboxs = self.tracker.update(bboxes, small_frame)
                    
                    # 在显示帧上绘制边界框 - 需要将坐标缩放回显示分辨率
                    scaled_bboxs = []
                    for bbox in list_bboxs:
                        x1, y1, x2, y2, label, track_id = bbox
                        # 缩放回显示分辨率
                        scaled_x1 = int(x1 * (self.display_width / self.process_width))
                        scaled_y1 = int(y1 * (self.display_height / self.process_height))
                        scaled_x2 = int(x2 * (self.display_width / self.process_width))
                        scaled_y2 = int(y2 * (self.display_height / self.process_height))
                        scaled_bboxs.append((scaled_x1, scaled_y1, scaled_x2, scaled_y2, label, track_id))
                    
                    output_image_frame = self.tracker.draw_bboxes(display_frame, scaled_bboxs, line_thickness=None)
                else:
                    output_image_frame = display_frame
                
                # 在显示分辨率的帧上添加多边形
                display_polygons = cv2.resize(color_polygons_image, (self.display_width, self.display_height))
                # 使用更高效的图像混合方法
                output_image_frame = cv2.addWeighted(output_image_frame, 1.0, display_polygons, 0.4, 0)

                if len(list_bboxs) > 0:
                    for item_bbox in list_bboxs:
                        x1, y1, x2, y2, label, track_id = item_bbox
                        x = x1
                        y = y2
                        
                        # 检查四个角点是否与多边形重叠，提高检测精度
                        check_points = [
                            (x1, y1),  # 左上
                            (x2, y1),  # 右上
                            (x1, y2),  # 左下
                            (x2, y2),  # 右下
                            ((x1+x2)//2, (y1+y2)//2)  # 中心点
                        ]
                        
                        # 检查对象是否与蓝色或黄色多边形重叠
                        # 在处理分辨率下检查，增加重叠容差
                        blue_overlap = False
                        yellow_overlap = False
                        
                        for px, py in check_points:
                            # 确保点在图像范围内
                            if 0 <= py < polygon_mask_blue_and_yellow.shape[0] and 0 <= px < polygon_mask_blue_and_yellow.shape[1]:
                                # 检查中心点周围的区域
                                for dy in range(-self.overlap_margin, self.overlap_margin+1):
                                    for dx in range(-self.overlap_margin, self.overlap_margin+1):
                                        ny, nx = py + dy, px + dx
                                        # 确保扩展点也在图像范围内
                                        if (0 <= ny < polygon_mask_blue_and_yellow.shape[0] and 
                                            0 <= nx < polygon_mask_blue_and_yellow.shape[1]):
                                            if polygon_mask_blue_and_yellow[ny, nx] == 1:
                                                blue_overlap = True
                                            elif polygon_mask_blue_and_yellow[ny, nx] == 2:
                                                yellow_overlap = True
                        
                        # 如果检测到蓝色区域重叠
                        if blue_overlap and track_id not in list_overlapping_blue_polygon:
                            count += 1
                            list_overlapping_blue_polygon.append(track_id)
                            start = processed_frames
                            print(f"检测到蓝色区域重叠！ID: {track_id}, 帧: {processed_frames}")

                        # 如果检测到黄色区域重叠
                        if yellow_overlap and track_id not in list_overlapping_yellow_polygon:
                            count += 1
                            ending = processed_frames
                            list_overlapping_yellow_polygon.append(track_id)
                            print(f"检测到黄色区域重叠！ID: {track_id}, 帧: {processed_frames}")

                k = ending - start
                if k > 0:
                    # 根据帧数差计算速度，考虑帧跳过因素
                    speed = round(4.0 * fps / (k * self.frame_skip), 2)
                    self.speed = speed  # 保存速度值
                    
                    # 如果已经获得有效的速度值且count达到2（一个完整的测速过程），立即停止处理
                    if count >= 2 and len(list_overlapping_blue_polygon) > 0 and len(list_overlapping_yellow_polygon) > 0:
                        print(f"Speed calculated: {speed} m/s, stopping early!")
                        print(f"Blue region objects: {list_overlapping_blue_polygon}")
                        print(f"Yellow region objects: {list_overlapping_yellow_polygon}")
                        self.speed_calculated = True  # 标记已完成测速
                        
                        # 直接跳到结果显示，无需继续处理后续帧
                        break  # 直接跳出循环，结束处理
                
                # 在显示帧上绘制文本信息
                text_draw = "Count: " + str(count) + " Speed: " + str(speed) + "m/s"
                output_image_frame = cv2.putText(img=output_image_frame, text=text_draw, org=(10, 50),
                                               fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(255, 0, 0),
                                               thickness=2)

                # 额外显示处理信息
                processing_info = f"Frame: {frame_number}/{int(frame_count)} Skip: {self.frame_skip} Res: {self.process_width}x{self.process_height}"
                output_image_frame = cv2.putText(img=output_image_frame, text=processing_info, org=(10, 90),
                                               fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.7, color=(0, 255, 0),
                                               thickness=2)
                
                # 在检测到蓝色或黄色区域重叠时，在画面上标记
                if len(list_overlapping_blue_polygon) > 0:
                    cv2.putText(output_image_frame, "Blue region detected", (10, 130), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                if len(list_overlapping_yellow_polygon) > 0:
                    cv2.putText(output_image_frame, "Yellow region detected", (10, 170), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                qt_img = self.convert_cv_to_qt(output_image_frame)
                self.change_pixmap_signal.emit(qt_img)

                progress = int((frame_number / frame_count) * 100)
                self.progress_signal.emit(progress)

                # 检查是否已经有测速结果且已经处理了足够多的帧
                if speed > 0 and frame_number > frame_count * self.early_stop_threshold:
                    print(f"提前结束处理：已处理{frame_number}/{int(frame_count)}帧，速度={speed}m/s")
                    break
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break

        # 如果有最后一帧，显示处理结果
        if last_display_frame is not None and speed > 0:
            # 创建一个带有最终结果的图像
            result_frame = last_display_frame.copy()
            # 绘制大号的速度文本
            result_text = f"Final Speed: {speed} m/s"
            cv2.putText(result_frame, result_text, (int(self.display_width/2) - 250, int(self.display_height/2)), 
                      cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
            # 根据测速是否提前完成显示不同信息
            if self.speed_calculated:
                processing_info = f"Speed calculation complete! Processed {processed_frames} frames"
                cv2.putText(result_frame, processing_info, (int(self.display_width/2) - 250, int(self.display_height/2) + 50), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # 添加一些测速细节
                time_info = f"Time: {k * self.frame_skip / fps:.2f} seconds for 4 meters"
                cv2.putText(result_frame, time_info, (int(self.display_width/2) - 250, int(self.display_height/2) + 100), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                processing_info = f"Processed {processed_frames} frames (every {self.frame_skip} frame)"
                cv2.putText(result_frame, processing_info, (int(self.display_width/2) - 250, int(self.display_height/2) + 50), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 转换为Qt图像并发送
            qt_img = self.convert_cv_to_qt(result_frame)
            self.change_pixmap_signal.emit(qt_img)

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
