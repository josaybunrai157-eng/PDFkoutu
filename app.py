#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF/图片处理工具 - 精简版
参考设计：单页面 + 红框检测 + 区域限制 + 批量上传
"""

import streamlit as st
import fitz
import cv2
import numpy as np
from PIL import Image
import hashlib
from pathlib import Path
import io

# 配置
CACHE_DIR = Path("/Users/niu/.openclaw/workspace/pdf_image_tool/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="PDF/图片处理工具", page_icon="📄", layout="wide")

# ========== 工具函数 ==========

def get_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

def pdf_to_images(pdf_bytes):
    """PDF 转图片"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        images.append((f"page_{page_num + 1:03d}.png", img_bytes))
    doc.close()
    return images

def process_image(img_array, x_start, y_start, x_end, y_end, method="inpaint", draw_box=False):
    """处理图片：去水印 + 红框"""
    result = img_array.copy()
    
    # 绘制红框（预览用）
    if draw_box:
        cv2.rectangle(result, (int(x_start), int(y_start)), (int(x_end), int(y_end)), (0, 0, 255), 3)
    
    # 去水印
    if method == "inpaint":
        mask = np.zeros(result.shape[:2], dtype=np.uint8)
        cv2.rectangle(mask, (int(x_start), int(y_start)), (int(x_end), int(y_end)), 255, -1)
        result = cv2.inpaint(result, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    elif method == "blur":
        roi = result[y_start:y_end, x_start:x_end]
        blurred = cv2.GaussianBlur(roi, (21, 21), 0)
        result[y_start:y_end, x_start:x_end] = blurred
    elif method == "median":
        roi = result[y_start:y_end, x_start:x_end]
        median_color = np.median(roi, axis=(0, 1)).astype(np.uint8)
        result[y_start:y_end, x_start:x_end] = median_color
    
    return result

# ========== 界面 ==========

st.title("📄 PDF/图片处理工具")
st.markdown("**批量处理 · 去水印 · 红框检测**")
st.markdown("---")

# ========== 侧边栏 ==========
st.sidebar.header("⚙️ 处理设置")

# 红框检测
enable_red_box = st.sidebar.toggle("🔴 开启红框检测", value=True, help="先预览 AI 框选区域是否正确")

# 区域限制
st.sidebar.subheader("🎯 区域限制（防误删）")
enable_region_limit = st.sidebar.toggle("只处理右下角特定区域", value=True)

if enable_region_limit:
    st.sidebar.markdown("*拖动滑块，注意中间的正文大字*")
    x_start_pct = st.sidebar.slider("识别区起始 X 轴（靠右）", 0, 100, 50, step=5)
    y_start_pct = st.sidebar.slider("识别区起始 Y 轴（靠下）", 0, 100, 70, step=5)
else:
    x_start_pct = 0
    y_start_pct = 0

# 去水印方法
st.sidebar.subheader("🛠️ 去水印方法")
method_map = {"修复算法 (Inpaint)": "inpaint", "高斯模糊": "blur", "中值覆盖": "median"}
watermark_method = st.sidebar.selectbox("选择算法", list(method_map.keys()), index=0)

# 水印尺寸
st.sidebar.subheader("📏 水印尺寸")
watermark_width_pct = st.sidebar.slider("水印宽度（占图片宽度）", 5, 50, 20, step=5)
watermark_height_pct = st.sidebar.slider("水印高度（占图片高度）", 2, 20, 10, step=2)

# ========== 文件上传 ==========
st.subheader("📤 批量上传图片或 PDF")
st.markdown("每个文件大小限制为 200MB")

uploaded_files = st.file_uploader(
    "将文件拖放到此处",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

# ========== 处理 ==========
if uploaded_files:
    st.markdown(f"✅ 已选择 **{len(uploaded_files)}** 个文件")
    
    if st.button("🚀 开始处理", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        all_results = []
        
        for i, file in enumerate(uploaded_files):
            file_bytes = file.read()
            file_hash = get_file_hash(file_bytes)
            file_name = file.name
            
            status_text.text(f"正在处理 ({i+1}/{len(uploaded_files)}): {file_name}")
            
            # 缓存
            cache_key = f"{file_hash}_{x_start_pct}_{y_start_pct}_{watermark_method}"
            cached_dir = CACHE_DIR / cache_key
            
            if cached_dir.exists() and not enable_red_box:
                # 使用缓存（红框预览时不使用缓存）
                result_files = []
                for img_path in sorted(cached_dir.glob("*.png")):
                    with open(img_path, "rb") as f:
                        result_files.append((img_path.name, f.read()))
                all_results.append((file_name, result_files, True))
            else:
                # 处理
                if not cached_dir.exists():
                    cached_dir.mkdir(parents=True, exist_ok=True)
                
                result_files = []
                
                # PDF 转图片
                if file_name.lower().endswith(".pdf"):
                    images = pdf_to_images(file_bytes)
                else:
                    img = Image.open(io.BytesIO(file_bytes))
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    images = [(file_name, buf.getvalue())]
                
                # 处理每张图片
                for img_name, img_bytes in images:
                    img = Image.open(io.BytesIO(img_bytes))
                    img_array = np.array(img.convert("RGB"))
                    h, w = img_array.shape[:2]
                    
                    # 计算区域
                    if enable_region_limit:
                        x_start = int(w * x_start_pct / 100)
                        y_start = int(h * y_start_pct / 100)
                    else:
                        x_start, y_start = 0, 0
                    
                    x_end = min(w, x_start + int(w * watermark_width_pct / 100))
                    y_end = min(h, y_start + int(h * watermark_height_pct / 100))
                    
                    # 处理
                    draw_box = enable_red_box
                    result_array = process_image(img_array, x_start, y_start, x_end, y_end, method_map[watermark_method], draw_box)
                    
                    # 保存
                    buf = io.BytesIO()
                    Image.fromarray(result_array).save(buf, format="PNG")
                    result_bytes = buf.getvalue()
                    result_files.append((img_name, result_bytes))
                    
                    # 缓存（不画红框时才缓存）
                    if not draw_box:
                        cache_path = cached_dir / img_name
                        Image.fromarray(result_array).save(cache_path)
                
                all_results.append((file_name, result_files, False))
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.text("✅ 处理完成！")
        
        # 显示结果
        with results_container:
            st.markdown("---")
            st.subheader("📋 处理结果")
            
            for file_name, results, is_cached in all_results:
                st.markdown(f"### 📄 {file_name} {'(缓存)' if is_cached else ''}")
                cols = st.columns(min(3, len(results)))
                for j, (img_name, img_bytes) in enumerate(results):
                    with cols[j % 3]:
                        st.image(img_bytes, caption=img_name, use_container_width=True)
                        st.download_button(
                            label=f"⬇️ 下载",
                            data=img_bytes,
                            file_name=img_name,
                            mime="image/png",
                            key=f"dl_{file_name}_{j}"
                        )
        
        progress_bar.empty()
        status_text.empty()

# ========== 页脚 ==========
st.markdown("---")
st.markdown("""
💡 **使用提示**：
1. **开启红框检测** 可以先预览处理区域是否正确
2. **区域限制** 可以防止误删正文内容（只处理右下角）
3. 处理结果会自动缓存，相同参数不会重复处理
""")
