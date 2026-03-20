# PDF/图片处理工具 📄

基于 Streamlit 的 PDF 和图片处理工具，支持 PDF 转图片、去水印、红点测试等功能。

## 功能特性

### 1. PDF 转图片 + 去水印
- 上传 PDF 自动逐页切分成图片
- 支持启用去水印功能
- 可调节水印位置（X/Y 轴）
- 可调节水印大小（宽度/高度）
- 3 种去水印算法：修复算法、模糊覆盖、高斯模糊

### 2. 图片去水印 + 红点测试
- **去水印模式**：同 PDF 模式
- **红点测试模式**：
  - 可调节红点位置（X/Y 轴）
  - 可调节红点大小
  - 可自定义红点颜色

### 3. 批量处理
- 支持一次上传多个 PDF 或图片
- 自动批量处理

### 4. 缓存机制
- 相同文件 + 相同参数 = 直接使用缓存
- 避免重复处理，提升效率

## 安装依赖

```bash
pip3 install --user streamlit pymupdf opencv-python-headless pillow numpy
```

## 运行程序

```bash
cd pdf_image_tool
streamlit run app.py --server.port 8501
```

然后在浏览器访问：http://localhost:8501

## 项目结构

```
pdf_image_tool/
├── app.py              # 主程序
├── uploads/            # 上传文件目录
├── outputs/            # 输出结果目录
├── cache/              # 缓存目录
├── .gitignore          # Git 忽略文件
└── README.md           # 说明文档
```

## 部署方案

### 本地部署
直接运行 `streamlit run app.py`

### Streamlit Cloud（免费）
1. 将代码推送到 GitHub
2. 访问 https://share.streamlit.io
3. 连接 GitHub 仓库
4. 选择 `app.py` 作为主文件
5. 点击部署

### 微信小程序（需要改造）
Streamlit 不能直接在小程序运行，需要：
1. 后端：使用 Flask/FastAPI 重写 API
2. 前端：使用微信小程序原生开发或 uni-app
3. 图片处理：使用云函数或后端服务器

### APP 打包（iOS/Android）
方案 1：使用 PyInstaller 打包成桌面应用
```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```

方案 2：使用 BeeWare/Toga 打包成移动应用（复杂）

方案 3（推荐）：部署到服务器，用 WebView 封装成 APP

## 技术栈

- **前端**：Streamlit
- **PDF 处理**：PyMuPDF (fitz)
- **图片处理**：OpenCV, Pillow
- **缓存**：文件哈希 + 本地存储

## 许可证

MIT License

## 作者

Created for 宿州弱电工程 - 监控安装/网络布线/门禁系统
