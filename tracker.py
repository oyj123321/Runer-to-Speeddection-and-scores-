import cv2
import torch
import numpy as np

from deep_sort.utils.parser import get_config
from deep_sort.deep_sort import DeepSort

cfg = get_config()
cfg.merge_from_file("./deep_sort/configs/deep_sort.yaml")
deepsort = DeepSort(cfg.DEEPSORT.REID_CKPT,
                    max_dist=cfg.DEEPSORT.MAX_DIST, min_confidence=cfg.DEEPSORT.MIN_CONFIDENCE,
                    nms_max_overlap=cfg.DEEPSORT.NMS_MAX_OVERLAP, max_iou_distance=cfg.DEEPSORT.MAX_IOU_DISTANCE,
                    max_age=cfg.DEEPSORT.MAX_AGE, n_init=cfg.DEEPSORT.N_INIT, nn_budget=cfg.DEEPSORT.NN_BUDGET,
                    use_cuda=True)


def draw_bboxes(image, bboxes, line_thickness):
    '''函数接受三个参数：image 是输入的图像，bboxes 是包含边界框信息的列表，line_thickness 是边界框和标签的线条粗细。
首先，代码根据图像的大小计算出默认的线条粗细 line_thickness。计算公式为图像宽度和高度的平均值的 0.002 倍，再加上 1。
然后，代码遍历 bboxes 列表中的每个边界框的坐标 (x1, y1, x2, y2)，类别标识符 cls_id 和位置标识符 pos_id。
代码设置边界框的颜色为绿色 (0, 255, 0)。
接下来，代码使用 cv2.rectangle 函数在图像上绘制边界框。c1 和 c2 分别表示边界框的左上角和右下角坐标。
然后，代码根据线条粗细设置字体的粗细 font_thickness，并使用 cv2.getTextSize 函数计算标签文本的大小 t_size。
接着，代码根据 t_size 和 c1 的坐标计算出标签背景框的右下角坐标 c2，然后使用 cv2.rectangle 函数绘制填充的标签背景框。
最后，代码使用 cv2.putText 函数在图像上绘制带有类别标识符和位置标识符的文本。文本的位置为 c1 的坐标，字体大小为线条粗细的 1/3 倍，颜色为白色 (225, 255, 255)。
最后，函数返回绘制了边界框和标签的图像。'''
    line_thickness = line_thickness or round(
        0.002 * (image.shape[0] + image.shape[1]) * 0.5) + 1

    for (x1, y1, x2, y2, cls_id, pos_id) in bboxes:
        color = (0, 255, 0)

        c1, c2 = (x1, y1), (x2, y2)
        cv2.rectangle(image, c1, c2, color, thickness=line_thickness, lineType=cv2.LINE_AA)

        font_thickness = max(line_thickness - 1, 1)
        t_size = cv2.getTextSize(cls_id, 0, fontScale=line_thickness / 3, thickness=font_thickness)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(image, c1, c2, color, -1, cv2.LINE_AA)  # filled
        cv2.putText(image, '{} ID-{}'.format(cls_id, pos_id), (c1[0], c1[1] - 2), 0, line_thickness / 3,
                    [225, 255, 255], thickness=font_thickness, lineType=cv2.LINE_AA)

    return image


def update(bboxes, image):
    '''函数接受两个参数：bboxes 是包含边界框信息的列表，image 是当前帧的图像。
首先，代码初始化了三个空列表 bbox_xywh、confs 和 bboxes2draw，用于存储中间结果和最终的边界框信息。
然后，代码判断如果 bboxes 列表的长度大于 0，则进入循环。循环遍历 bboxes 列表中的每个边界框的坐标 (x1, y1, x2, y2)，标签 lbl 和置信度 conf。
在循环中，代码计算出边界框的中心坐标 (cx, cy) 和宽高 (w, h)，并将这些信息以列表形式 obj 存储在 bbox_xywh 列表中。
同时，代码将置信度 conf 存储在 confs 列表中，并将标签 lbl 存储在 label 变量中。
接下来，代码将 bbox_xywh 列表和 confs 列表转换为 PyTorch 的 Tensor 对象 xywhs 和 confss。
然后，代码调用 deepsort.update 函数，传入 xywhs、confss 和当前帧的图像 image，获取跟踪后的输出结果 outputs。
最后，代码将跟踪后的输出结果转换为 (x1, y1, x2, y2, label, track_id) 格式的边界框信息，并添加到 bboxes2draw 列表中。
最后，函数返回包含更新后的边界框信息的 bboxes2draw 列表。'''
    bbox_xywh = []
    confs = []
    bboxes2draw = []

    if len(bboxes) > 0:
        for x1, y1, x2, y2, lbl, conf in bboxes:
            obj = [
                int((x1 + x2) * 0.5), int((y1 + y2) * 0.5),
                x2 - x1, y2 - y1
            ]
            bbox_xywh.append(obj)
            confs.append(conf)
            label = lbl

        xywhs = torch.Tensor(bbox_xywh)
        confss = torch.Tensor(confs)

        outputs = deepsort.update(xywhs, confss, image)

        for x1, y1, x2, y2, track_id in list(outputs):

            bboxes2draw.append((x1, y1, x2, y2, label, track_id))

    return bboxes2draw

