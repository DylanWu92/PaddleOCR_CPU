#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR-VL 图形用户界面
提供简单直观的界面进行OCR识别操作
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from datetime import datetime
# 导入PaddleOCR-VL相关模块
from PaddleOCRVL_main import get_pipeline, ocr_image

class OCRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PaddleOCR-VL 文本识别工具")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.root.configure(bg="#f0f0f0")
        
        # 设置中文字体支持
        self.default_font = ("Microsoft YaHei", 10)
        self.title_font = ("Microsoft YaHei", 12, "bold")
        
        # 变量初始化
        self.selected_files = []
        self.output_dir = "output/gui_results"
        os.makedirs(self.output_dir, exist_ok=True)
        self.ocr_running = False
        self.ocr_pipeline = None  # PaddleOCR-VL模型实例
        
        # 创建主框架
        self.create_widgets()
        
        # 初始化状态栏
        self.update_status("正在初始化OCR模型...")
        
        # 在单独线程中初始化OCR模型，避免界面卡顿
        threading.Thread(target=self.initialize_ocr, daemon=True).start()
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 创建顶部控制栏
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X, side=tk.TOP)
        
        # 选择文件按钮
        select_btn = ttk.Button(control_frame, text="选择图片文件", command=self.select_files)
        select_btn.pack(side=tk.LEFT, padx=5)
        
        # 选择文件夹按钮
        select_folder_btn = ttk.Button(control_frame, text="选择图片文件夹", command=self.select_folder)
        select_folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 开始识别按钮
        self.start_btn = ttk.Button(control_frame, text="开始识别", command=self.start_recognition, state=tk.DISABLED)  # 初始禁用，等待OCR初始化完成
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        # 清除列表按钮
        clear_btn = ttk.Button(control_frame, text="清除列表", command=self.clear_file_list)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 导出结果按钮
        export_btn = ttk.Button(control_frame, text="导出结果", command=self.export_results)
        export_btn.pack(side=tk.LEFT, padx=5)
        
        # 创建分割线
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)
        
        # 创建主内容区域（使用PanedWindow进行分割）
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧文件列表框架
        left_frame = ttk.LabelFrame(main_paned, text="待处理文件", padding="5")
        main_paned.add(left_frame, weight=1)
        
        # 文件列表
        self.file_listbox = tk.Listbox(left_frame, font=self.default_font, selectmode=tk.EXTENDED)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        # 右侧结果展示框架
        right_frame = ttk.LabelFrame(main_paned, text="识别结果", padding="5")
        main_paned.add(right_frame, weight=2)
        
        # 结果展示区域（分为上下两部分）
        right_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)
        
        # 图片预览区域
        preview_frame = ttk.LabelFrame(right_paned, text="图片预览", padding="5")
        right_paned.add(preview_frame, weight=1)
        
        # 预览画布
        self.preview_canvas = tk.Canvas(preview_frame, bg="#e0e0e0")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 文本结果区域
        result_frame = ttk.LabelFrame(right_paned, text="文本结果", padding="5")
        right_paned.add(result_frame, weight=1)
        
        # 文本结果显示
        self.result_text = tk.Text(result_frame, font=self.default_font, wrap=tk.WORD, undo=True)
        self.result_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # 文本滚动条
        text_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=text_scrollbar.set)
        
        # 创建状态栏
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, font=self.default_font)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, mode="determinate")
        self.progress_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.progress_bar.pack_forget()  # 初始隐藏
        
        # 绑定事件
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_selected)
    
    def select_files(self):
        """选择单个或多个图片文件"""
        supported_formats = [
            ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp *.gif"),
            ("JPG文件", "*.jpg *.jpeg"),
            ("PNG文件", "*.png"),
            ("所有文件", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=supported_formats
        )
        
        if files:
            # 添加文件到列表，避免重复
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    self.file_listbox.insert(tk.END, os.path.basename(file))
            
            self.update_status(f"已选择 {len(files)} 个文件")
    
    def select_folder(self):
        """选择包含图片的文件夹"""
        folder = filedialog.askdirectory(title="选择图片文件夹")
        
        if folder:
            # 获取文件夹中所有支持的图片文件
            supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif'}
            new_files = []
            
            try:
                for root_dir, _, files in os.walk(folder):
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if ext in supported_extensions:
                            full_path = os.path.join(root_dir, file)
                            if full_path not in self.selected_files:
                                self.selected_files.append(full_path)
                                self.file_listbox.insert(tk.END, f"{os.path.basename(root_dir)}/{file}")
                                new_files.append(full_path)
                
                if new_files:
                    self.update_status(f"从文件夹添加了 {len(new_files)} 个图片文件")
                else:
                    messagebox.showinfo("提示", "所选文件夹中没有找到支持的图片文件")
                    self.update_status("就绪")
            
            except Exception as e:
                messagebox.showerror("错误", f"读取文件夹时出错: {str(e)}")
                self.update_status("就绪")
    
    def clear_file_list(self):
        """清除文件列表"""
        if messagebox.askyesno("确认", "确定要清除所有文件吗？"):
            self.selected_files.clear()
            self.file_listbox.delete(0, tk.END)
            self.result_text.delete(1.0, tk.END)
            self.clear_preview()
            self.update_status("文件列表已清空")
    
    def on_file_selected(self, event):
        """当用户在文件列表中选择文件时"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        # 获取选中的文件索引
        index = selection[0]
        file_path = self.selected_files[index]
        
        # 更新预览
        self.update_preview(file_path)
        
        # 尝试加载已有的识别结果
        self.load_saved_result(file_path)
    
    def update_preview(self, file_path):
        """更新图片预览"""
        try:
            # 清除之前的预览
            self.clear_preview()
            
            # 打开并调整图片大小
            image = Image.open(file_path)
            canvas_width = self.preview_canvas.winfo_width() - 20
            canvas_height = self.preview_canvas.winfo_height() - 20
            
            # 保持图片比例
            image.thumbnail((canvas_width, canvas_height), Image.LANCZOS)
            
            # 转换为Tkinter可用的格式
            self.photo_image = ImageTk.PhotoImage(image)
            
            # 计算居中位置
            x = (canvas_width - image.width) // 2
            y = (canvas_height - image.height) // 2
            
            # 在画布上显示图片
            self.preview_image_id = self.preview_canvas.create_image(
                x + 10, y + 10, anchor=tk.NW, image=self.photo_image
            )
            
        except Exception as e:
            self.preview_canvas.create_text(
                50, 50, anchor=tk.NW, text=f"无法预览图片:\n{str(e)}", 
                font=self.default_font, fill="red"
            )
    
    def on_canvas_configure(self, event):
        """当画布大小改变时重新调整预览"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            file_path = self.selected_files[index]
            self.update_preview(file_path)
    
    def clear_preview(self):
        """清除图片预览"""
        self.preview_canvas.delete("all")
        self.photo_image = None
    
    def load_saved_result(self, file_path):
        """加载已保存的识别结果"""
        # 生成对应的结果文件路径
        image_name = os.path.splitext(os.path.basename(file_path))[0]
        result_dir = os.path.join(self.output_dir, image_name)
        result_file = os.path.join(result_dir, "ocr_result.txt")
        
        # 尝试读取结果文件
        if os.path.exists(result_file):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.result_text.delete(1.0, tk.END)
                    self.result_text.insert(tk.END, content)
            except Exception as e:
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, f"无法加载保存的结果: {str(e)}")
        else:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "尚未进行OCR识别")
    
    def initialize_ocr(self):
        """初始化OCR模型"""
        try:
            # 初始化PaddleOCR-VL模型
            self.ocr_pipeline = get_pipeline()
            self.root.after(0, lambda: self.update_status("PaddleOCR-VL模型初始化完成，就绪"))
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
        except Exception as e:
            error_msg = f"PaddleOCR-VL模型初始化失败: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, lambda: self.update_status("PaddleOCR-VL模型初始化失败"))
    
    def start_recognition(self):
        """开始OCR识别"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择要识别的图片文件")
            return
        
        if self.ocr_running:
            messagebox.showinfo("提示", "识别正在进行中，请稍候")
            return
        
        if self.ocr_pipeline is None:
            messagebox.showinfo("提示", "OCR模型正在初始化，请稍候...")
            return
        
        # 禁用开始按钮
        self.start_btn.config(state=tk.DISABLED)
        self.ocr_running = True
        self.progress_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.progress_var.set(0)
        
        # 在单独的线程中运行识别，避免界面冻结
        threading.Thread(target=self.run_ocr_in_thread, daemon=True).start()
    
    def run_ocr_in_thread(self):
        """在单独线程中执行OCR识别"""
        total_files = len(self.selected_files)
        success_count = 0
        failed_count = 0
        start_time = time.time()
        
        for i, file_path in enumerate(self.selected_files, 1):
            # 更新状态
            filename = os.path.basename(file_path)
            self.root.after(0, lambda msg=f"正在识别 {i}/{total_files}: {filename}": self.update_status(msg))
            
            try:
                # 直接调用OCR模型进行识别
                result = self.ocr_single_image(file_path)
                
                if result:
                    success_count += 1
                    
                    # 更新UI
                    self.root.after(0, lambda idx=i: self.highlight_processed_file(idx))
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"处理失败: {str(e)}"
                print(error_msg)
            
            # 更新进度条
            progress = (i / total_files) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))
        
        # 计算总耗时
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 完成后的清理工作
        self.root.after(0, self.ocr_completed, success_count, failed_count, elapsed_time)
    
    def ocr_single_image(self, image_path):
        """对单个图片进行OCR识别"""
        try:
            # 检查文件是否存在
            if not os.path.exists(image_path):
                error_msg = f"文件不存在: {image_path}"
                print(error_msg)
                
                # 创建输出目录并保存错误信息
                image_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = os.path.join(self.output_dir, image_name)
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, "ocr_result.txt")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"图片文件: {os.path.basename(image_path)}\n")
                    f.write(f"错误: {error_msg}\n")
                return False
            
            # 规范化路径格式
            image_path = os.path.abspath(image_path)
            
            # 创建输出目录
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            output_dir = os.path.join(self.output_dir, image_name)
            os.makedirs(output_dir, exist_ok=True)
            
            print(f"正在处理图片: {image_path}")
            
            # 使用PaddleOCR-VL进行识别
            # 这里我们直接调用PaddleOCRVL_main中的ocr_image函数进行识别
            # 注意：ocr_image函数会自动保存markdown和json格式的结果到指定目录
            texts = []
            result = None
            
            try:
                # 确保ocr_image函数被正确调用
                print(f"开始调用ocr_image函数处理: {image_path}")
                result = ocr_image(image_path, output_dir=output_dir, print_result=True)  # 设为True获取详细日志
                
                # 调试：打印原始结果
                print(f"ocr_image返回结果类型: {type(result)}")
                print(f"ocr_image返回结果: {result}")
                
                # 尝试读取JSON格式的结果，获取位置信息
                structured_results = []
                json_result_path = os.path.join(output_dir, f"{image_name}_result.json")
                if os.path.exists(json_result_path):
                    try:
                        import json
                        with open(json_result_path, 'r', encoding='utf-8') as f:
                            structured_results = json.load(f)
                        print(f"成功加载结构化结果，共 {len(structured_results)} 个文本块")
                    except Exception as json_error:
                        print(f"读取JSON结果失败: {json_error}")
                
                # 如果有结构化结果（带位置信息），按位置排序
                if structured_results:
                    # 按y坐标分组，实现按行排序
                    line_groups = self.group_text_by_lines(structured_results)
                    # 对每行内的文本按x坐标排序
                    formatted_text = self.format_lines_text(line_groups)
                    texts = [formatted_text]
                    print(f"已根据位置信息重新排序文本，生成了格式化输出")
                else:
                    # 处理各种可能的结果类型
                    if result is None:
                        print("[ERROR] ocr_image返回None值")
                        texts = ["OCR识别失败: 函数返回空结果"]
                    elif isinstance(result, list):
                        print(f"[INFO] 收到列表类型结果，长度: {len(result)}")
                        
                        # 直接使用列表中的字符串项
                        for i, item in enumerate(result):
                            print(f"  结果项 {i} 类型: {type(item)}")
                            if isinstance(item, str):
                                text = item.strip()
                                if text:
                                    texts.append(text)
                                    print(f"  添加文本: '{text[:50]}...'" if len(text) > 50 else f"  添加文本: '{text}'")
                        
                        # 如果没有有效文本，提供反馈
                        if not texts and result:
                            print("[警告] 结果列表中没有有效字符串")
                            # 尝试将整个结果转换为字符串
                            texts = [f"OCR结果: {str(result)}"]
                        elif not result:
                            print("[警告] 结果列表为空")
                            texts = ["OCR识别成功，但返回空列表"]
                    else:
                        # 非列表类型，转换为字符串
                        print(f"[INFO] 收到非列表类型结果: {type(result)}")
                        text_str = str(result)
                        if text_str.strip():
                            texts = [text_str]
                            print(f"  转换为字符串: '{text_str[:50]}...'" if len(text_str) > 50 else f"  转换为字符串: '{text_str}'")
                        else:
                            texts = ["OCR识别结果为空字符串"]
            except Exception as e:
                error_msg = f"OCR处理异常: {str(e)}"
                print(error_msg)
                import traceback
                traceback.print_exc()
                texts = [error_msg]
            
            # 确保始终有输出内容
            if not texts:
                print("[CRITICAL] 未能提取任何文本内容")
                texts = ["OCR处理未能提取文本，请查看日志获取详细信息"]
            
            # 保存原始结果用于调试
            try:
                with open(os.path.join(output_dir, 'raw_results.txt'), 'w', encoding='utf-8') as f:
                    f.write(str(result))
            except Exception as e:
                print(f"保存原始结果时出错: {str(e)}")
            
            # 保存结果到文件
            output_file = os.path.join(output_dir, "ocr_result.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                if texts:
                    for text in texts:
                        f.write(f"{text}\n")
                else:
                    # 如果没有识别到文本，尝试从原始结果提取
                    f.write(str(result))
            
            print(f"识别完成，保存结果到: {output_file}")
            return True
            
        except Exception as e:
            error_msg = f"OCR识别错误: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            
            # 保存错误信息到文件
            try:
                image_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = os.path.join(self.output_dir, image_name)
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, "ocr_result.txt")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"图片文件: {os.path.basename(image_path)}\n")
                    f.write(f"错误: {error_msg}\n")
            except:
                pass
            
            return False
    
    def get_text_block_center_y(self, text_block):
        """计算文本块的中心y坐标，用于行分组"""
        try:
            position = text_block.get('position', [])
            if isinstance(position, list) and len(position) >= 2:
                # 假设position是包含四个角点坐标的列表，取顶部和底部y坐标的平均值
                if isinstance(position[0], (list, tuple)) and isinstance(position[2], (list, tuple)):
                    # 格式: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    top_y = min(point[1] for point in position if isinstance(point, (list, tuple)) and len(point) >= 2)
                    bottom_y = max(point[1] for point in position if isinstance(point, (list, tuple)) and len(point) >= 2)
                    return (top_y + bottom_y) / 2
            return 0
        except:
            return 0
    
    def get_text_block_left_x(self, text_block):
        """获取文本块的最左侧x坐标，用于水平排序"""
        try:
            position = text_block.get('position', [])
            if isinstance(position, list):
                if isinstance(position[0], (list, tuple)):
                    # 格式: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    return min(point[0] for point in position if isinstance(point, (list, tuple)) and len(point) >= 2)
                elif len(position) >= 2:
                    # 简化格式: [x, y, width, height]或类似格式
                    return position[0]
            return 0
        except:
            return 0
    
    def group_text_by_lines(self, text_blocks):
        """根据y坐标将文本块分组为行"""
        if not text_blocks:
            return []
        
        # 复制一份并添加中心y坐标
        blocks_with_y = []
        for block in text_blocks:
            if isinstance(block, dict) and 'text' in block:
                y_center = self.get_text_block_center_y(block)
                blocks_with_y.append((block, y_center))
        
        # 按y坐标排序
        blocks_with_y.sort(key=lambda x: x[1])
        
        # 分组行，相似y坐标的文本块视为同一行
        lines = []
        current_line = []
        current_y = None
        line_threshold = 15  # 行高阈值，可根据需要调整
        
        for block, y in blocks_with_y:
            if current_line == []:
                current_line.append(block)
                current_y = y
            else:
                # 如果当前文本块的y坐标与当前行的平均y坐标相差不大，则视为同一行
                if abs(y - current_y) <= line_threshold:
                    current_line.append(block)
                else:
                    # 否则开始新行
                    lines.append(current_line)
                    current_line = [block]
                    current_y = y
        
        # 添加最后一行
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def detect_table_structure(self, line_groups):
        """检测表格结构，返回表格行和列信息"""
        if len(line_groups) < 2:  # 至少需要两行才能构成表格
            return False, [], []
        
        # 计算每一行的文本块x坐标位置，用于检测对齐列
        column_positions = []
        for line in line_groups:
            if len(line) > 1:  # 每行至少需要两个文本块
                sorted_line = sorted(line, key=self.get_text_block_left_x)
                positions = [self.get_text_block_left_x(block) for block in sorted_line]
                column_positions.append(positions)
        
        # 如果有多行都有类似的列结构，则可能是表格
        if len(column_positions) >= 2:
            # 检查列数是否一致
            column_counts = [len(pos) for pos in column_positions]
            if len(set(column_counts)) <= 2:  # 允许小的变化
                # 检查列对齐情况
                avg_columns = sum(column_counts) / len(column_counts)
                if avg_columns >= 2:  # 至少2列
                    # 提取每列的平均x坐标位置
                    max_columns = max(column_counts)
                    avg_column_positions = []
                    for col_idx in range(max_columns):
                        col_positions = []
                        for row_positions in column_positions:
                            if col_idx < len(row_positions):
                                col_positions.append(row_positions[col_idx])
                        if col_positions:
                            avg_column_positions.append(sum(col_positions) / len(col_positions))
                    
                    # 如果表格有足够的列，返回表格结构
                    if len(avg_column_positions) >= 2:
                        return True, line_groups, avg_column_positions
        
        return False, [], []
    
    def format_table_text(self, line_groups, column_positions):
        """格式化表格文本，使用|分隔符"""
        table_lines = []
        
        # 确定每列的最大宽度
        max_widths = []
        for col_idx in range(len(column_positions)):
            max_width = 0
            for line in line_groups:
                if col_idx < len(line):
                    text_len = len(line[col_idx].get('text', ''))
                    max_width = max(max_width, text_len)
            max_widths.append(max_width)
        
        # 生成表头分隔线
        separator = '+'
        for width in max_widths:
            separator += '-' * (width + 2) + '+'
        
        table_lines.append(separator)
        
        # 格式化每一行
        for line in line_groups:
            # 按x坐标排序
            sorted_line = sorted(line, key=self.get_text_block_left_x)
            
            # 构建行文本
            row_text = '|'
            for col_idx, block in enumerate(sorted_line):
                text = block.get('text', '')
                # 根据列宽格式化文本，添加适当的填充
                if col_idx < len(max_widths):
                    row_text += ' ' + text.ljust(max_widths[col_idx]) + ' |'
                else:
                    row_text += ' ' + text + ' |'
            
            table_lines.append(row_text)
            table_lines.append(separator)
        
        return '\n'.join(table_lines)
    
    def format_lines_text(self, line_groups):
        """格式化行文本，支持表格检测和格式化"""
        # 尝试检测表格结构
        is_table, table_lines, column_positions = self.detect_table_structure(line_groups)
        
        if is_table:
            print(f"检测到表格结构，共 {len(table_lines)} 行 {len(column_positions)} 列")
            return self.format_table_text(table_lines, column_positions)
        else:
            # 普通文本格式化
            formatted_lines = []
            
            for line in line_groups:
                # 每行内按x坐标排序
                sorted_line = sorted(line, key=self.get_text_block_left_x)
                # 合并文本
                line_text = ' '.join(block.get('text', '') for block in sorted_line)
                if line_text.strip():
                    formatted_lines.append(line_text.strip())
            
            # 合并所有行，用换行符分隔
            return '\n'.join(formatted_lines)
    
    def highlight_processed_file(self, index):
        """高亮显示已处理的文件"""
        self.file_listbox.itemconfig(index - 1, bg="#d0f0d0")
    
    def ocr_completed(self, success, failed, elapsed_time):
        """OCR识别完成后的处理"""
        # 恢复UI状态
        self.start_btn.config(state=tk.NORMAL)
        self.ocr_running = False
        self.progress_bar.pack_forget()
        
        # 显示完成信息
        message = f"识别完成！\n成功: {success}个文件\n失败: {failed}个文件\n总耗时: {elapsed_time:.2f}秒"
        self.update_status(f"识别完成: 成功{success}个，失败{failed}个")
        
        # 更新当前选中文件的结果
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            file_path = self.selected_files[index]
            self.load_saved_result(file_path)
        
        # 显示完成消息
        messagebox.showinfo("完成", message)
    
    def export_results(self):
        """导出所有识别结果到一个文件"""
        if not os.path.exists(self.output_dir):
            messagebox.showwarning("警告", "没有识别结果可导出")
            return
        
        # 让用户选择保存位置
        export_file = filedialog.asksaveasfilename(
            title="导出结果",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=f"ocr_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if export_file:
            try:
                with open(export_file, "w", encoding="utf-8") as f:
                    f.write(f"OCR识别结果汇总\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    # 遍历所有处理过的文件
                    for i, file_path in enumerate(self.selected_files, 1):
                        image_name = os.path.splitext(os.path.basename(file_path))[0]
                        result_file = os.path.join(self.output_dir, image_name, "ocr_result.txt")
                        
                        if os.path.exists(result_file):
                            f.write(f"\n[文件 {i}] {os.path.basename(file_path)}\n")
                            f.write("-" * 60 + "\n")
                            
                            with open(result_file, "r", encoding="utf-8") as rf:
                                f.write(rf.read())
                            
                            f.write("\n" + "=" * 80 + "\n")
                
                messagebox.showinfo("成功", f"结果已成功导出到:\n{export_file}")
                self.update_status(f"结果已导出到: {os.path.basename(export_file)}")
            
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")
                self.update_status("导出失败")
    
    def update_status(self, message):
        """更新状态栏消息"""
        self.status_var.set(f"  {message}")

def main():
    """主函数"""
    # 设置中文字体
    root = tk.Tk()
    
    # 创建应用实例
    app = OCRGUI(root)
    
    # 运行主循环
    root.mainloop()

if __name__ == "__main__":
    main()