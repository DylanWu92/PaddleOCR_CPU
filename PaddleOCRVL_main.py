#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR-VL 主模块
提供OCR识别功能，包含智能回退机制
"""

import os
import sys
import traceback
import numpy as np
from PIL import Image

# 全局变量，用于缓存模型实例
_pipeline = None
# 标记是否使用了回退方案
_using_fallback = False
# 标记是否已经尝试过初始化
_initialization_attempted = False

def get_pipeline():
    """
    获取或创建OCR pipeline实例
    直接使用标准PaddleOCR以避免paddlex重复初始化问题
    """
    global _pipeline, _using_fallback, _initialization_attempted
    
    # 如果已经初始化过，直接返回缓存的实例
    if _pipeline is not None:
        return _pipeline
    
    # 如果已经尝试过初始化但失败了，避免重复尝试
    if _initialization_attempted:
        raise RuntimeError("之前的OCR初始化已失败，请重启程序后重试")
    
    _initialization_attempted = True
    print("正在初始化OCR模型...")
    
    # 直接尝试使用标准PaddleOCR，避免paddlex重复初始化问题
    try:
        print("尝试使用标准PaddleOCR...")
        # 直接使用PaddleOCR的ocr模块，避免导入整个paddleocr包
        try:
            from paddleocr import PaddleOCR
            print("成功导入PaddleOCR")
            # 使用更简单的参数配置，减少初始化复杂性
            _pipeline = PaddleOCR(use_angle_cls=True, lang='ch')
            print("成功初始化标准PaddleOCR")
            _using_fallback = True
            return _pipeline
        except Exception as paddle_error:
            print(f"初始化PaddleOCR时出错: {str(paddle_error)}")
            raise
    except Exception as e:
        error_msg = f"OCR初始化失败: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        raise RuntimeError(error_msg)

def is_using_fallback():
    """
    检查当前是否使用了回退方案
    """
    global _using_fallback
    return _using_fallback

def ocr_image(image_path, output_dir="output", print_result=True):
    """执行OCR识别并返回纯文本结果"""

    """
    对单个图片进行 OCR 识别
    
    参数:
        image_path: 图片路径
        output_dir: 结果保存目录
        print_result: 是否打印识别结果
    
    返回:
        识别结果列表
    """
    print(f"ocr_image: 开始处理图片: {image_path}")
    
    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        print(f"ocr_image: 错误 - 图片文件不存在: {image_path}")
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    try:
        print(f"ocr_image: 确保输出目录存在: {output_dir}")
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        print("ocr_image: 获取OCR pipeline实例...")
        # 获取pipeline和回退状态
        pipeline = get_pipeline()
        using_fallback = is_using_fallback()
        print(f"ocr_image: pipeline初始化完成, 是否使用回退方案: {using_fallback}")
        
        if print_result:
            print(f"使用的OCR引擎: {'标准PaddleOCR' if using_fallback else 'PaddleOCR-VL'}")
            print(f"\n正在执行 OCR 识别: {image_path}")
        
        # 根据不同的 pipeline 类型调用对应的方法
        try:
            print(f"ocr_image: 检查pipeline类型: {type(pipeline)}")
            # 先使用PIL预处理图片，避免paddlex图片读取器的问题
            print("ocr_image: 使用PIL预处理图片...")
            try:
                img = Image.open(image_path)
                # 转换RGBA为RGB
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                # 转换为numpy数组
                img_array = np.array(img)
                print(f"ocr_image: 图片预处理成功，形状: {img_array.shape}")
                
                # 优先使用predict方法（根据警告提示）
                if hasattr(pipeline, 'predict'):
                    print("ocr_image: 使用predict方法进行识别")
                    output = pipeline.predict(img_array)
                    print(f"ocr_image: 预测完成, 返回结果类型: {type(output)}")
                    # 处理output为None的情况
                    if output is None:
                        print("[ERROR] predict方法返回None值")
                        output = []
                elif using_fallback or hasattr(pipeline, 'ocr'):
                    print("ocr_image: 使用ocr方法进行识别")
                    output = pipeline.ocr(img_array)
                    print(f"ocr_image: OCR识别完成, 返回结果类型: {type(output)}")
                    # 处理output为None的情况
                    if output is None:
                        print("[ERROR] ocr方法返回None值")
                        output = []
                else:
                    error_msg = f"不支持的 pipeline 类型: {type(pipeline)}"
                    print(f"ocr_image: 错误 - {error_msg}")
                    raise ValueError(error_msg)
            except Exception as preprocess_error:
                # 如果预处理失败，尝试直接使用路径
                print(f"ocr_image: 图片预处理失败，尝试直接使用路径: {str(preprocess_error)}")
                if using_fallback or hasattr(pipeline, 'ocr'):
                    output = pipeline.ocr(image_path)
                elif hasattr(pipeline, 'predict'):
                    output = pipeline.predict(image_path)
                else:
                    raise ValueError(f"不支持的 pipeline 类型: {type(pipeline)}")
        except Exception as predict_error:
            error_msg = f"执行 OCR 预测时出错: {str(predict_error)}"
            print(f"ocr_image: 错误 - {error_msg}")
            traceback.print_exc()
            raise RuntimeError(error_msg) from predict_error
        
        if print_result:
            print("="*80)
            print("识别结果:")
            print("="*80)
        
        # 为每个图片创建单独的输出文件夹
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        save_path = os.path.join(output_dir, image_name)
        os.makedirs(save_path, exist_ok=True)
        
        # 处理不同类型的输出结果
        standard_results = []
        
        try:
            # 根据不同的结果格式进行处理
            if using_fallback and isinstance(output, list) and len(output) > 0 and isinstance(output[0], list):
                # 标准PaddleOCR格式: [[[坐标], [文本, 置信度]], ...]
                for line in output[0]:  # 标准PaddleOCR返回的是双层列表
                    if len(line) >= 2 and isinstance(line[1], (list, tuple)) and len(line[1]) >= 1:
                        text = line[1][0] if line[1] else ""
                        score = line[1][1] if len(line[1]) > 1 else 1.0
                        position = line[0] if isinstance(line[0], (list, tuple)) else []
                        
                        standard_results.append({
                            'text': text,
                            'score': score,
                            'position': position
                        })
                        
                        if print_result:
                            print(f"文本: {text}, 置信度: {score:.4f}")
            else:
                # PaddleOCR-VL或其他格式处理
                if isinstance(output, list):
                    for line in output:
                        if isinstance(line, dict):
                            # 处理字典格式
                            text = line.get('text', line.get('rec_texts', ''))
                            score = line.get('score', 1.0)
                            position = line.get('position', line.get('coordinates', []))
                            
                            standard_results.append({
                                'text': text,
                                'score': score,
                                'position': position
                            })
                            
                            if print_result:
                                print(f"文本: {text}, 置信度: {score:.4f}")
                        elif isinstance(line, (list, tuple)) and len(line) > 0:
                            # 处理列表或元组格式
                            if isinstance(line[0], (list, tuple)) and len(line) > 1:
                                # 处理[[坐标], 文本]格式
                                text = line[1] if isinstance(line[1], str) else str(line[1])
                                standard_results.append({
                                    'text': text,
                                    'score': 1.0,
                                    'position': line[0]
                                })
                                
                                if print_result:
                                    print(f"文本: {text}")
                            else:
                                # 其他列表格式
                                if print_result:
                                    print(f"未知格式: {line}")
                else:
                    # 原有的OCRVL对象格式处理
                    if hasattr(output, '__iter__') and not isinstance(output, (str, dict)):
                        for idx, res in enumerate(output):
                            if print_result:
                                print(f"\n页面 {idx + 1}:")
                                # 根据不同类型的结果采用不同的打印方式
                                if hasattr(res, 'print'):
                                    res.print()
                                else:
                                    print(res)
            
            # 保存结果为JSON和Markdown格式
            json_path = os.path.join(save_path, f"{image_name}_result.json")
            md_path = os.path.join(save_path, f"{image_name}_result.md")
            
            # 保存为JSON
            import json
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(standard_results, f, ensure_ascii=False, indent=2)
            
            # 保存为Markdown
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# {image_name}\n\n")
                f.write("## OCR识别结果\n\n")
                f.write(f"**使用引擎**: {'标准PaddleOCR' if using_fallback else 'PaddleOCR-VL'}\n\n")
                for idx, item in enumerate(standard_results, 1):
                    f.write(f"### 文本 {idx}\n")
                    f.write(f"```\n{item['text']}\n```\n")
                    if 'score' in item:
                        f.write(f"**置信度**: {item['score']:.4f}\n\n")
                    else:
                        f.write("\n")
            
            # 保留原有的保存方法（如果结果对象支持）
            if hasattr(output, '__iter__') and not isinstance(output, (str, dict)):
                for res in output:
                    if hasattr(res, 'save_to_json'):
                        res.save_to_json(save_path=save_path)
                    if hasattr(res, 'save_to_markdown'):
                        res.save_to_markdown(save_path=save_path)
            
        except Exception as save_error:
            print(f"保存结果时出错: {str(save_error)}")
        
        if print_result:
            print(f"\n[完成] 结果已保存到 {save_path} 目录")
            
            # 返回纯文本结果，确保与原文保持一致并保留换行格式
            # 直接从standard_results中提取文本内容，不做额外处理
            pure_text_results = []
            for item in standard_results:
                # 直接添加原始文本，保留所有字符包括换行符
                if isinstance(item, dict):
                    # 尝试多种可能的文本键名
                    text_keys = ['text', 'content', 'value', 'recognition_result']
                    for key in text_keys:
                        if key in item:
                            text = item[key]
                            # 检查文本是否为列表，如果是则展平
                            if isinstance(text, list):
                                for t in text:
                                    # 确保添加的是字符串
                                    if isinstance(t, str):
                                        pure_text_results.append(t)
                            elif isinstance(text, str):
                                pure_text_results.append(text)
                            break
                elif isinstance(item, (str, tuple)):
                    # 直接添加字符串或转换元组为字符串
                    text = str(item)
                    if text.strip():
                        pure_text_results.append(text)
                elif hasattr(item, '__str__'):
                    # 尝试转换其他对象为字符串
                    text = str(item)
                    if text.strip():
                        pure_text_results.append(text)
            # 确保返回的结果不为空
            if not pure_text_results:
                print("[WARNING] 无法从OCR结果中提取任何文本")
                pure_text_results = ["未识别到明确的文本内容"]
            
            print(f"[DEBUG] 最终返回的文本结果数量: {len(pure_text_results)}")
            return pure_text_results
    except Exception as e:
        print(f"OCR 处理过程中发生错误: {str(e)}")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    # 单张图片测试示例
    test_image = r"C:\Users\gotmo\Pictures\Screenshots\Snipaste_2025-10-09_14-21-01.png"
    if os.path.exists(test_image):
        try:
            ocr_image(test_image)
            print("OCR 测试完成")
        except Exception as e:
            print(f"OCR 测试失败: {str(e)}")
            sys.exit(1)
    else:
        print(f"测试图片不存在: {test_image}")
        print("请使用 batch_ocr.py 进行批量处理，或修改此处的图片路径")
        sys.exit(1)
