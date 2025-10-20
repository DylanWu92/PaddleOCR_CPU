# PaddleOCR_CPU 安装与使用教程

## 项目简介

PaddleOCR-VL_CPU 是一个基于 PaddlePaddle 的 OCR（光学字符识别）系统，专为CPU环境优化，支持中文文本识别、表格检测和结构化输出。本项目提供了图形界面，方便用户快速进行图片文字识别、发票内容提取等操作。

主要功能：
- 高精度文本识别（支持中英文及多种语言）
- 智能表格检测与格式化输出
- 基于位置坐标的文本重排，保持原文布局
- 用户友好的图形界面
- 支持批量图片处理
- CPU环境优化，无需GPU支持

## 环境要求

### 硬件要求
- CPU：支持Intel/AMD处理器，推荐4核及以上
- 内存：建议8GB及以上
- 存储空间：至少1GB（用于安装依赖和模型文件）

### 软件要求
- 操作系统：Windows 10/11
- Python版本：Python 3.7 - 3.11
- 依赖库：PaddlePaddle、OpenCV、NumPy、Tkinter等

## 安装步骤

### 1. 安装Python

如果您的系统中尚未安装Python，请先下载并安装：

1. 访问 [Python官网](https://www.python.org/downloads/)
2. 下载Python 3.7-3.11版本的安装包
3. 安装时勾选"Add Python to PATH"选项
4. 完成安装后，打开命令提示符验证安装：
   ```
   python --version
   pip --version
   ```

### 2. 克隆项目

使用Git克隆项目到本地（如果没有Git，也可以直接下载ZIP文件并解压）：

```bash
git clone https://github.com/dylanwu92/PaddleOCR_CPU.git
cd PaddleOCR_CPU
```

如果是下载ZIP文件，请解压后进入项目目录：

```bash
cd PaddleOCR_CPU-main
```

### 3. 创建虚拟环境（推荐）

为避免依赖冲突，建议创建一个虚拟环境：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 激活虚拟环境（macOS/Linux）
# source venv/bin/activate
```

### 4. 安装依赖库

安装项目所需的Python库：

```bash
# 升级pip
pip install --upgrade pip

# 安装PaddlePaddle（CPU版本）
pip install paddlepaddle==2.5.0 -i https://mirror.baidu.com/pypi/simple

# 安装PaddleOCR
pip install paddleocr==2.7.0.3

# 安装其他依赖
pip install opencv-python numpy pillow
```

### 5. 模型文件下载

首次运行程序时，系统会自动下载所需的OCR模型文件到用户目录下的`.paddlex/official_models/`文件夹中。主要包括：

- PP-LCNet_x1_0_doc_ori：文档分类模型
- UVDoc：文档理解模型
- PP-LCNet_x1_0_textline_ori：文本行检测模型
- PP-OCRv5_server_det：文字检测模型
- PP-OCRv5_server_rec：文字识别模型

> 注意：模型文件总大小约为200-300MB，请确保网络连接稳定。

## 使用方法

### 通过图形界面使用

1. 启动GUI程序：

```bash
python ocr_gui.py
```

2. 使用界面功能：
   - 点击"选择文件"按钮选择一个或多个图片文件
   - 点击"开始识别"按钮开始OCR处理
   - 查看识别结果，系统会自动检测表格并格式化输出
   - 结果将保存在`output/gui_results/`目录下

### 命令行使用（高级用户）

可以直接使用`PaddleOCRVL_main.py`中的函数进行OCR处理：

```python
from PaddleOCRVL_main import ocr_image

# 对单个图片进行OCR识别
result = ocr_image('path/to/your/image.jpg', output_dir='./output')
print(result)
```

## 输出文件说明

处理完成后，系统会在`output/gui_results/图片名称/`目录下生成以下文件：

- `ocr_result.txt`：OCR识别的文本结果，表格会以格式化形式显示
- `图片名称_result.json`：结构化的识别结果，包含文本内容、位置坐标和置信度
- `图片名称_result.md`：Markdown格式的结果报告
- `raw_results.txt`：原始OCR结果，用于调试

## 表格识别功能

本系统能够自动检测图片中的表格结构，并以ASCII表格格式输出，例如：

```
+--------+---------+---------+
| 项目   | 数量    | 单价    |
+--------+---------+---------+
| 商品A  | 2       | 100.00  |
+--------+---------+---------+
| 商品B  | 1       | 200.00  |
+--------+---------+---------+
```

表格检测基于文本块的位置坐标分析，能够准确识别并保持表格的行列结构。

## 常见问题与解决方案

### 1. 程序无法启动或模型下载失败

- 确保网络连接正常
- 检查Python版本是否符合要求（3.7-3.11）
- 尝试重新安装PaddleOCR：`pip install paddleocr==2.7.0.3 --force-reinstall`

### 2. OCR识别结果不准确

- 确保图片清晰，文字不模糊
- 调整图片对比度，确保文字与背景有足够的区分度
- 对于复杂表格，可能需要调整表格检测参数（在`ocr_gui.py`中的`detect_table_structure`函数）

### 3. 表格检测失败

- 表格线必须清晰可见
- 表格结构不能过于复杂或不规则
- 可以尝试调整`ocr_gui.py`中的`line_threshold`参数（默认为15）

## 性能优化建议

- 对于批量处理，建议每次处理的图片数量不要过多（10-20张为宜）
- 对于大尺寸图片，可以先进行适当的缩放再进行识别
- 确保系统有足够的内存（8GB以上）以获得最佳性能

## 系统架构

- **PaddleOCRVL_main.py**：核心OCR处理逻辑，负责调用PaddleOCR引擎并处理识别结果
- **ocr_gui.py**：图形用户界面，提供文件选择、识别控制和结果显示功能
- **表格检测模块**：自动识别并格式化表格结构
- **文本重排模块**：基于位置坐标优化文本输出布局

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的OCR识别功能
- 提供图形用户界面

### v1.1.0
- 新增文本重排功能，基于位置坐标优化输出格式
- 修复部分识别错误

### v1.2.0
- 新增表格检测和格式化输出功能
- 优化GUI性能
- 改进错误处理机制

## 许可证

本项目基于Apache License 2.0许可证发布。

## 致谢

- 感谢PaddlePaddle团队提供的OCR引擎
- 感谢所有为项目做出贡献的开发者

## 联系方式

如有问题或建议，请通过以下方式联系我们：
- 项目GitHub仓库：[[GitHub链接](https://github.com/DylanWu92/PaddleOCR_CPU)]
- 邮箱:w545317335@163.com
