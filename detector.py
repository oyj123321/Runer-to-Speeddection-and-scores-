import torch
import numpy as np

from models.experimental import attempt_load
from utils.datasets import letterbox
from utils.general import non_max_suppression, scale_coords
from utils.torch_utils import select_device


class Detector:

    def __init__(self):
        self.img_size = 640
        self.threshold = 0.6
        self.stride = 1

        self.weights = './weights/yolov5m.pt'

        self.device = '0' if torch.cuda.is_available() else 'cpu'
        print(torch.cuda.is_available())
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

    def preprocess(self, img):

        img0 = img.copy()  # 创建一个原始图像 img 的副本 img0，以便后续使用
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

        return img0, img  # 返回处理后的原始图像 img0 和预处理后的图像 img

    def detect(self, im):
        im0, img = self.preprocess(im)  # 调用 preprocess() 函数对输入图像进行预处理。这个函数将输入图像进行缩放、归一化等操作，返回原始图像 im0 和处理后的图像 img
        pred = self.m(img, augment=True)[0]
        '''将处理后的图像 img 输入到 YOLOv5 模型 self.m 中进行推断
        augment=False 参数表示不使用数据增强技术
        模型的输出 pred 是一个列表，包含了检测框的坐标、类别标签、置信度等信息'''
        pred = pred.float()  # 将模型输出的数据类型转换为浮点型
        pred = non_max_suppression(pred, self.threshold, 0.4)
        '''对模型输出进行非最大抑制（Non-Maximum Suppression）
        去除重叠的检测框并保留置信度较高的检测结果
        self.threshold 参数是阈值，用于过滤掉置信度低于阈值的检测结果'''

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

        return boxes
