#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF/图片处理工具
功能：
1. PDF 转图片（逐页切分）+ 去水印
2. 图片去水印 + 红点测试
3. 缓存机制
4. 可调节去水印位置（X/Y 轴）
"""

import streamlit as st
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import os
import hashlib
from pathlib import Path

# 配置
UPLOAD_DIR = Path("/Users/niu/.openclaw/workspace/pdf_image_tool/uploads")
OUTPUT_DIR = Path("/Users/niu/.openclaw/workspace/pdf_image_tool/outputs")
CACHE_DIR = Path("/Users/niu/.openclaw/workspace/pdf_image_tool/cache")

# 创建目录
for d in [UPLOAD_DIR, OUTPUT_DIR, CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="PDF/图片处理工具", page_icon="📄", layout="wide")

# ========== 工具函数 ==========

def get_file_hash(file):
    """计算文件哈希值用于缓存"""
    file.seek(0)
    content = file.read()
    return hashlib.md5(content).hexdigest()

def pdf_to_images(pdf_path, output_dir):
    """PDF 转图片"""
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2 倍分辨率
        img_path = output_dir / f"page_{page_num + 1:03d}.png"
        pix.save(str(img_path))
        images.append(img_path)
    doc.close()
    return images

def remove_watermark_inpaint(image_path, mask, output_path):
    """使用 OpenCV 修复算法去水印"""
    img = cv2.imread(str(image_path))
    if img is None:
        return None
    
    # 确保 mask 是单通道
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)
    
    # 使用修复算法
    result = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    cv2.imwrite(str(output_path), result)
    return output_path

def create_rect_mask(img_shape, x, y, width, height):
    """创建矩形水印遮罩"""
    mask = np.zeros(img_shape[:2], dtype=np.uint8)
    cv2.rectangle(mask, (x, y), (x + width, y + height), 255, -1)
    return mask

# ========== 界面 ==========

st.title("📄 PDF/图片处理工具")
st.markdown("---")

# 侧边栏 - 功能选择
st.sidebar.header("功能选择")
mode = st.sidebar.radio(
    "选择模式",
    ["PDF 转图片", "图片去水印", "批量处理"],
    index=0
)

# ========== 模式 1: PDF 转图片 + 去水印 ==========
if mode == "PDF 转图片":
    st.header("📑 PDF 转图片 + 去水印")
    
    uploaded_file = st.file_uploader("上传 PDF 文件", type=["pdf"])
    
    if uploaded_file:
        # 侧边栏 - 去水印设置
        st.sidebar.subheader("去水印设置")
        enable_watermark_removal = st.sidebar.checkbox("启用去水印", value=False)
        
        if enable_watermark_removal:
            wm_x = st.sidebar.slider("水印 X 轴位置", 0, 2000, 0, step=10)
            wm_y = st.sidebar.slider("水印 Y 轴位置", 0, 2000, 0, step=10)
            wm_width = st.sidebar.slider("水印宽度", 10, 2000, 200, step=10)
            wm_height = st.sidebar.slider("水印高度", 10, 2000, 50, step=10)
            wm_method = st.sidebar.selectbox(
                "去水印算法",
                ["修复算法 (Inpaint)", "模糊覆盖", "高斯模糊"],
                index=0
            )
        
        # 检查缓存
        file_hash = get_file_hash(uploaded_file)
        cache_key = f"pdf_{file_hash}"
        if enable_watermark_removal:
            cache_key += f"_wm_{wm_x}_{wm_y}_{wm_width}_{wm_height}_{wm_method}"
        cached_dir = CACHE_DIR / cache_key
        
        if cached_dir.exists():
            st.info(f"✅ 使用缓存结果")
            images = list(cached_dir.glob("*.png"))
        else:
            # 保存并转换
            uploaded_file.seek(0)
            pdf_path = UPLOAD_DIR / uploaded_file.name
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.read())
            
            with st.spinner("正在转换 PDF..."):
                output_subdir = OUTPUT_DIR / f"pdf_{file_hash}"
                output_subdir.mkdir(parents=True, exist_ok=True)
                images = pdf_to_images(pdf_path, output_subdir)
                
                # 去水印处理
                if enable_watermark_removal:
                    with st.spinner("正在去水印..."):
                        watermarked_images = []
                        for i, img_path in enumerate(images):
                            img = cv2.imread(str(img_path))
                            if wm_method == "修复算法 (Inpaint)":
                                mask = create_rect_mask(img.shape, wm_x, wm_y, wm_width, wm_height)
                                result = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
                            elif wm_method == "模糊覆盖":
                                result = img.copy()
                                result[wm_y:wm_y+wm_height, wm_x:wm_x+wm_width] = np.median(result[wm_y:wm_y+wm_height, wm_x:wm_x+wm_width], axis=(0, 1))
                            else:  # 高斯模糊
                                result = img.copy()
                                roi = result[wm_y:wm_y+wm_height, wm_x:wm_x+wm_width]
                                result[wm_y:wm_y+wm_height, wm_x:wm_x+wm_width] = cv2.GaussianBlur(roi, (21, 21), 0)
                            
                            wm_path = output_subdir / f"page_{i+1:03d}_nowm.png"
                            cv2.imwrite(str(wm_path), result)
                            watermarked_images.append(wm_path)
                        images = watermarked_images
                
                # 存入缓存
                cached_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                for img in images:
                    dest = cached_dir / img.name
                    if not dest.exists():
                        shutil.copy(img, dest)
            
            st.success(f"✅ 转换完成！共 {len(images)} 页")
        
        # 显示结果
        st.subheader("转换结果")
        cols = st.columns(3)
        for i, img_path in enumerate(images):
            with cols[i % 3]:
                st.image(str(img_path), caption=f"第 {i+1} 页", use_container_width=True)
        
        # 下载按钮
        st.subheader("下载")
        for i, img_path in enumerate(images):
            with open(img_path, "rb") as f:
                st.download_button(
                    label=f"下载 第{i+1}页",
                    data=f.read(),
                    file_name=f"page_{i+1:03d}.png",
                    mime="image/png",
                    key=f"dl_{i}"
                )

# ========== 模式 2: 图片去水印 + 红点测试 ==========
elif mode == "图片去水印":
    st.header("🖼️ 图片去水印 + 红点测试")
    
    uploaded_file = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"])
    
    if uploaded_file:
        file_hash = get_file_hash(uploaded_file)
        cache_key = f"watermark_{file_hash}"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("原图")
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
        
        with col2:
            st.subheader("处理后")
        
        # 侧边栏设置
        st.sidebar.subheader("功能选择")
        feature = st.sidebar.radio(
            "选择功能",
            ["去水印", "红点测试"],
            index=0
        )
        
        uploaded_file.seek(0)
        img_array = np.array(image)
        img_shape = img_array.shape
        
        result = None
        
        if feature == "去水印":
            st.sidebar.markdown("### 水印位置")
            x = st.sidebar.slider("X 轴位置", 0, img_shape[1], 0, step=10)
            y = st.sidebar.slider("Y 轴位置", 0, img_shape[0], 0, step=10)
            width = st.sidebar.slider("水印宽度", 10, img_shape[1], 200, step=10)
            height = st.sidebar.slider("水印高度", 10, img_shape[0], 50, step=10)
            
            st.sidebar.markdown("### 去水印方法")
            method = st.sidebar.selectbox(
                "选择算法",
                ["修复算法 (Inpaint)", "模糊覆盖", "高斯模糊"],
                index=0
            )
            
            if st.sidebar.button("开始去水印"):
                cache_params = f"{x}_{y}_{width}_{height}_{method}"
                cached_file = CACHE_DIR / f"{cache_key}_{cache_params}.png"
                
                if cached_file.exists():
                    st.sidebar.success("✅ 使用缓存结果")
                    result = Image.open(cached_file)
                    with col2:
                        st.image(result, use_container_width=True)
                else:
                    with st.spinner("正在处理..."):
                        if method == "修复算法 (Inpaint)":
                            mask = create_rect_mask(img_shape, x, y, width, height)
                            temp_input = UPLOAD_DIR / f"temp_{file_hash}.png"
                            temp_output = OUTPUT_DIR / f"result_{file_hash}.png"
                            img_array_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                            cv2.imwrite(str(temp_input), img_array_bgr)
                            result_path = remove_watermark_inpaint(temp_input, mask, temp_output)
                            if result_path:
                                result = Image.open(result_path)
                                result.save(cached_file)
                                with col2:
                                    st.image(result, use_container_width=True)
                        
                        elif method == "模糊覆盖":
                            result_array = img_array.copy()
                            result_array[y:y+height, x:x+width] = np.median(result_array[y:y+height, x:x+width], axis=(0, 1))
                            result = Image.fromarray(result_array)
                            result.save(cached_file)
                            with col2:
                                st.image(result, use_container_width=True)
                        
                        elif method == "高斯模糊":
                            result_array = img_array.copy()
                            roi = result_array[y:y+height, x:x+width]
                            blurred = cv2.GaussianBlur(roi, (21, 21), 0)
                            result_array[y:y+height, x:x+width] = blurred
                            result = Image.fromarray(result_array)
                            result.save(cached_file)
                            with col2:
                                st.image(result, use_container_width=True)
                    
                    st.sidebar.success("✅ 处理完成！")
        
        elif feature == "红点测试":
            st.sidebar.markdown("### 红点位置")
            dot_x = st.sidebar.slider("红点 X 轴", 0, img_shape[1], img_shape[1]//2, step=5)
            dot_y = st.sidebar.slider("红点 Y 轴", 0, img_shape[0], img_shape[0]//2, step=5)
            dot_size = st.sidebar.slider("红点大小", 1, 50, 10, step=1)
            dot_color = st.sidebar.color_picker("红点颜色", "#ff0000")
            
            if st.sidebar.button("绘制红点"):
                cache_params = f"dot_{dot_x}_{dot_y}_{dot_size}_{dot_color}"
                cached_file = CACHE_DIR / f"{cache_key}_{cache_params}.png"
                
                if cached_file.exists():
                    st.sidebar.success("✅ 使用缓存结果")
                    result = Image.open(cached_file)
                    with col2:
                        st.image(result, use_container_width=True)
                else:
                    with st.spinner("正在绘制..."):
                        result_array = img_array.copy()
                        r = int(dot_color[1:3], 16)
                        g = int(dot_color[3:5], 16)
                        b = int(dot_color[5:7], 16)
                        center = (dot_x, dot_y)
                        radius = dot_size
                        cv2.circle(result_array, center, radius, (b, g, r), -1)
                        result = Image.fromarray(result_array)
                        result.save(cached_file)
                        with col2:
                            st.image(result, use_container_width=True)
                    
                    st.sidebar.success("✅ 红点已绘制！")
        
        # 下载按钮
        if result is not None:
            import io
            buf = io.BytesIO()
            result.save(buf, format="PNG")
            st.download_button(
                label="下载处理后的图片",
                data=buf.getvalue(),
                file_name=f"processed_{uploaded_file.name}",
                mime="image/png"
            )

# ========== 模式 3: 批量处理 ==========
elif mode == "批量处理":
    st.header("📦 批量处理")
    
    uploaded_files = st.file_uploader(
        "上传多个文件（PDF 或图片）",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.write(f"已选择 {len(uploaded_files)} 个文件")
        
        if st.button("开始批量处理"):
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                file_hash = get_file_hash(file)
                
                if file.name.lower().endswith(".pdf"):
                    pdf_path = UPLOAD_DIR / file.name
                    with open(pdf_path, "wb") as f:
                        f.write(file.read())
                    
                    output_subdir = OUTPUT_DIR / f"pdf_{file_hash}"
                    output_subdir.mkdir(parents=True, exist_ok=True)
                    pdf_to_images(pdf_path, output_subdir)
                
                else:
                    img = Image.open(file)
                    output_path = OUTPUT_DIR / f"img_{file_hash}.png"
                    img.save(output_path)
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            st.success("✅ 批量处理完成！")
            st.write(f"输出目录：{OUTPUT_DIR}")

# ========== 页脚 ==========
st.markdown("---")
st.markdown("💡 **提示**: 所有处理结果会缓存，相同参数不会重复处理")
