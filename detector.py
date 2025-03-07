import torch
import numpy as np
import cv2
import time

from models.experimental import attempt_load
from utils.datasets import letterbox
from utils.general import non_max_suppression, scale_coords
from utils.torch_utils import select_device


class Detector:

    def __init__(self):
        self.img_size = 640
        self.threshold = 0.5  # 略微降低阈值，提高检测率
        self.stride = 1

        self.weights = './weights/yolov5m.pt'

        self.device = '0' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {self.device}")
        self.device = select_device(self.device)

        '''加载 YOLOv5 模型的权重文件
        并将模型加载到设备上进行推断
        attempt_load() 函数用于加载模型
        map_location=self.device 参数用于指定模型加载到指定的设备'''
        model = attempt_load(self.weights, map_location=self.device)
        model.to(self.device).eval()  # 将模型移动到指定的设备，并设置为评估（推断）模式。这样做是为了确保模型在推断过程中的一致性
        model.float()
        '''将模型参数的数据类型设置为浮点型。这是因为 PyTorch 在默认情况下将模型参数的数据类型设置为双精度型，但在推断过程中，通常使用浮点型数据类型来加速计算'''

        self.m = model
        self.names = model.module.names if hasattr(
            model, 'module') else model.names
            
        # 优化设置
        self.batch_size = 1
        self.warmup_runs = 2
        
        # 性能优化 - 预热模型
        self.warmup()
        
        # 上一帧图像的特征缓存
        self.last_img = None
        self.last_features = None
        self.skip_count = 0  # 跳帧计数器
        self.max_skip = 2  # 降低最多连续跳过帧数，提高检测准确性
        
    def warmup(self):
        """预热模型，提高后续推理性能"""
        print("Warming up model...")
        # 创建一个随机输入
        dummy_input = torch.zeros((1, 3, self.img_size, self.img_size), device=self.device)
        # 进行几次预热运行
        for _ in range(self.warmup_runs):
            _ = self.m(dummy_input)
        print("Model warmup complete")

    def preprocess(self, img):
        img0 = img.copy()  # 创建一个原始图像 img 的副本 img0，以便后续使用
        
        # 检查图像相似度，如果图像与上一帧非常相似，可以考虑复用特征
        if self.last_img is not None and self.skip_count < self.max_skip:
            similarity = self.check_similarity(img, self.last_img)
            if similarity > 0.98:  # 提高相似度阈值，降低复用概率，增加检测准确性
                self.skip_count += 1
                # 返回None表示可以复用上一帧的特征
                return img0, None, True
        
        # 重置跳帧计数器
        self.skip_count = 0
        self.last_img = img.copy()
        
        img = letterbox(img, new_shape=self.img_size)[
            0]  # 函数对图像进行填充（或裁剪）操作，将图像大小调整为指定的 self.img_size 尺寸。返回的结果是调整后的图像 img
        img = img[:, :, ::-1].transpose(2, 0, 1)
        '''对调整后的图像 img 进行通道顺序转换和维度转置操作，
        将通道顺序从 BGR（Blue-Green-Red）转换为 RGB（Red-Green-Blue），
        并将通道维度从 HWC（高-宽-通道）转换为 CHW（通道-高-宽）。
        这样做是因为许多深度学习模型的输入要求为 RGB 通道顺序和 CHW 维度顺序'''
        img = np.ascontiguousarray(img)  # 将图像 img 转换为连续内存的数组。这是由于 PyTorch 要求输入的数据需要是连续内存的
        img = torch.from_numpy(img).to(self.device)  # 将图像 img 转换为 PyTorch 张量，并将其移动到指定的设备（例如 GPU）上进行加速计算
        img = img.float()  # 将图像数据类型转换为浮点型
        img /= 255.0  # 将图像像素值归一化到 [0, 1] 的范围，通过除以 255.0 实现
        if img.ndimension() == 3:
            '''如果图像的维度为 3，表示没有批次维度
            那么通过 unsqueeze(0) 在最前面添加一个维度
            以适应模型对输入的要求。'''
            img = img.unsqueeze(0)

        return img0, img, False
        
    def check_similarity(self, img1, img2):
        """检查两个图像的相似度"""
        try:
            # 转换为灰度
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # 调整大小以加快计算
            small1 = cv2.resize(gray1, (64, 64))  # 增大比较分辨率
            small2 = cv2.resize(gray2, (64, 64))  # 增大比较分辨率
            
            # 计算直方图相似度
            hist1 = cv2.calcHist([small1], [0], None, [16], [0, 256])  # 增加直方图bins
            hist2 = cv2.calcHist([small2], [0], None, [16], [0, 256])  # 增加直方图bins
            
            # 归一化直方图
            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
            
            # 计算相似度
            similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return similarity
        except:
            return 0  # 如果出错，返回0（不相似）

    def detect(self, im):
        im0, img, can_reuse = self.preprocess(im)  # 调用 preprocess() 函数对输入图像进行预处理
        
        # 如果可以复用上一帧特征，直接使用上一帧的检测结果
        if can_reuse and self.last_features is not None:
            # 复制上一帧的检测结果
            return self.last_features
        
        # 性能优化：加入超时机制
        start_time = time.time()
        max_inference_time = 1.0  # 增加最大推理时间，提高检测准确性
        
        pred = None
        with torch.no_grad():  # 禁用梯度计算以减少内存使用
            try:
                # 设置超时触发器（仅对CPU模式有效）
                if self.device == 'cpu':
                    # 使用较低的置信度阈值和IoU阈值，在CPU上的较低配置上也能工作
                    temp_threshold = max(0.45, self.threshold - 0.1)  # 适度降低检测阈值
                    temp_iou = 0.45  # 降低NMS的IoU阈值
                else:
                    temp_threshold = self.threshold
                    temp_iou = 0.4
                
                # 执行推理
                pred = self.m(img, augment=False)[0]  # 关闭augment以提高速度
                pred = pred.float()
                pred = non_max_suppression(pred, temp_threshold, temp_iou)
                
                # 检查是否超时
                if time.time() - start_time > max_inference_time:
                    print(f"Inference timeout: {time.time() - start_time:.2f}s, returning simplified result")
                    # 如果已经超时，使用简化的处理方法
                    boxes = []
                    if self.last_features is not None:
                        # 使用上一帧的检测结果
                        return self.last_features
                    else:
                        # 如果没有上一帧结果，返回空列表
                        return boxes
            except Exception as e:
                print(f"Inference error: {e}")
                # 如果发生错误，使用上一帧的结果
                if self.last_features is not None:
                    return self.last_features
                else:
                    return []

        boxes = []  # 创建一个空列表，用于存储检测到的目标框信息
        for det in pred:  # 遍历模型输出中的每个检测结果

            if det is not None and len(det):  # 检查检测结果是否为非空并且有检测到目标
                '''对检测框的坐标进行缩放和转换
                使其与原始图像的尺寸相匹配
                scale_coords() 函数用于将检测框的坐标从模型输出的特征图坐标系转换为原始图像坐标系'''
                det[:, :4] = scale_coords(
                    img.shape[2:], det[:, :4], im0.shape).round()

                # 遍历每个检测框的信息，包括坐标、置信度和类别标签
                for *x, conf, cls_id in det:
                    lbl = self.names[int(cls_id)]  # 根据类别标签的索引获取对应的类别名称
                    if lbl not in ['person']:
                        continue
                    pass
                    x1, y1 = int(x[0]), int(x[1])
                    x2, y2 = int(x[2]), int(x[3])
                    boxes.append(
                        (x1, y1, x2, y2, lbl, conf))
        
        # 保存当前帧的检测结果以供下一帧可能复用
        self.last_features = boxes
        
        # 打印检测到的目标数量
        if len(boxes) > 0:
            print(f"Detected {len(boxes)} persons")
        
        return boxes
