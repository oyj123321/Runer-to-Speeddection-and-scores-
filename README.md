# 运动员自动打分系统

## 项目简介

这是一个基于计算机视觉技术的运动员自动打分系统，能够通过分析运动员的动作视频，自动评估其技术动作的质量并给出分数。该系统利用深度学习模型识别和跟踪运动员的关键点，分析动作的标准度、流畅度和完成质量。

## 主要功能

- 视频输入：支持多种格式的视频文件输入
- 姿态识别：基于YOLOv5的人体姿态识别
- 动作分析：分析运动员动作的标准度和完成质量
- 自动评分：根据预设标准自动为运动员表现打分
- 结果可视化：生成包含评分和分析的可视化结果

## 技术栈

- Python 3.8+
- PyTorch 2.6+
- OpenCV
- YOLOv5
- NumPy
- Pandas

## 安装指南

### 环境要求

- Python 3.8或更高版本
- CUDA支持的GPU（推荐用于实时处理）

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/sports-scoring-system.git
cd sports-scoring-system
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 下载预训练模型（如果需要）
```bash
# 根据实际情况下载相应的预训练模型
```

## 使用方法

### 基本用法

```bash
python main.py --video path/to/video.mp4 --sport gymnastics
```

### 参数说明

- `--video`: 输入视频文件路径
- `--sport`: 运动类型（如体操、跳水、艺术体操等）
- `--output`: 输出结果保存路径（可选）
- `--visualize`: 是否生成可视化结果（可选，默认为True）

## 支持的运动类型

- 体操
- 跳水
- 艺术体操
- 花样滑冰
- 更多运动类型正在开发中...

## 系统架构

该系统主要由以下几个模块组成：

1. 视频处理模块：负责视频的读取、预处理和帧提取
2. 姿态识别模块：基于YOLOv5的人体姿态识别
3. 动作分析模块：分析运动员的动作序列
4. 评分模块：根据预设标准计算得分
5. 可视化模块：生成结果报告和可视化展示

## 注意事项

- 在PyTorch 2.6及以上版本中，`torch.load`的默认行为发生了变化，本项目已针对此进行了适配
- 为获得最佳性能，建议使用支持CUDA的GPU
- 不同运动类型可能需要不同的评分标准和模型参数

## 贡献指南

欢迎对本项目进行贡献！如果您有任何改进意见或发现了bug，请提交issue或pull request。

## 许可证

本项目采用MIT许可证。详情请参见LICENSE文件。

## 联系方式

如有任何问题或建议，请通过以下方式联系我们：

- 邮箱：your.email@example.com
- GitHub Issues
