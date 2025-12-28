# PDF to Markdown (去除参考文献)

将学术论文 PDF 批量转换为 Markdown，并自动删除参考文献部分。

## 功能

- ✅ 批量转换整个文件夹的 PDF
- ✅ 自动识别并删除 References / 参考文献 / Bibliography
- ✅ 跨平台支持 (macOS / Linux / Windows)
- ✅ 适用于原生数字 PDF（可选中文字的 PDF）

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/pdf2md-tool.git
cd pdf2md-tool
```

### 2. 安装依赖

**macOS:**
```bash
pip3 install --user --break-system-packages pymupdf4llm
```

**Linux:**
```bash
pip3 install --user pymupdf4llm
```

**Windows:**
```bash
pip install pymupdf4llm
```

## 使用方法

```bash
python pdf2md.py <PDF文件夹路径>
```

### 示例

```bash
# macOS / Linux
python3 pdf2md.py ./papers
python3 pdf2md.py ~/Documents/论文

# Windows
python pdf2md.py .\papers
python pdf2md.py C:\Users\你的用户名\Documents\论文
```

### 输出

转换后的 `.md` 文件保存在原 PDF 文件夹中：

```
papers/
├── paper1.pdf  →  paper1.md
├── paper2.pdf  →  paper2.md
└── paper3.pdf  →  paper3.md
```

## 原理

| 类型 | 说明 |
|------|------|
| 目标 PDF | 原生数字 PDF（文字可选中复制） |
| 技术 | 直接解析 PDF 内部结构，无需 OCR |
| 速度 | 秒级（每篇论文几秒） |
| 准确率 | 100%（直接提取，无识别错误） |

> ⚠️ 如果是扫描件 PDF（无法选中文字），此工具不适用，需要 OCR 工具如 marker-pdf。

## 自定义参考文献标题

如果你的论文使用特殊的参考文献标题格式，编辑 `pdf2md.py` 中的 `REFERENCE_PATTERNS` 列表添加新的匹配模式。

## License

MIT
