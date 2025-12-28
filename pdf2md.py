#!/usr/bin/env python3
"""
PDF to Markdown Converter for Academic Papers
将学术论文PDF转换为Markdown，并自动去除参考文献部分

跨平台支持：macOS / Linux / Windows
"""

import os
import sys
import re
from pathlib import Path

# ============ 配置区域 ============
# 参考文献标题关键词（可自定义添加）
REFERENCE_PATTERNS = [
    r'^#+\s*References?\s*$',
    r'^References?\s*$',
    r'^\*\*References?\*\*\s*$',
    r'^#+\s*参考文献\s*$',
    r'^参考文献\s*$',
    r'^#+\s*Bibliography\s*$',
    r'^Bibliography\s*$',
    r'^#+\s*REFERENCES?\s*$',
    r'^REFERENCES?\s*$',
]
# ==================================


def check_dependencies():
    """检查并提示安装依赖"""
    try:
        import pymupdf4llm
        return True
    except ImportError:
        print("=" * 50)
        print("  缺少依赖: pymupdf4llm")
        print("=" * 50)
        print("\n请运行以下命令安装:\n")
        
        if sys.platform == "darwin":  # macOS
            print("  pip3 install --user --break-system-packages pymupdf4llm")
        elif sys.platform == "win32":  # Windows
            print("  pip install pymupdf4llm")
        else:  # Linux
            print("  pip3 install --user pymupdf4llm")
        
        print()
        return False


def remove_references(md_content: str) -> tuple:
    """移除参考文献部分"""
    lines = md_content.split('\n')
    result_lines = []
    found = False
    
    for line in lines:
        for pattern in REFERENCE_PATTERNS:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                found = True
                break
        if found:
            break
        result_lines.append(line)
    
    # 移除末尾空行
    while result_lines and result_lines[-1].strip() == '':
        result_lines.pop()
    
    return '\n'.join(result_lines), found


def process_folder(folder_path: str):
    """处理文件夹中的所有 PDF"""
    import pymupdf4llm
    
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        print(f"✗ 无效路径: {folder_path}")
        sys.exit(1)
    
    # 支持大小写扩展名
    pdf_files = list(folder.glob("*.pdf")) + list(folder.glob("*.PDF"))
    
    if not pdf_files:
        print(f"✗ 未找到 PDF 文件: {folder_path}")
        sys.exit(1)
    
    print(f"\n找到 {len(pdf_files)} 个 PDF 文件\n")
    print("-" * 50)
    
    success = 0
    
    for i, pdf in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] {pdf.name}")
        
        try:
            md = pymupdf4llm.to_markdown(str(pdf))
        except Exception as e:
            print(f"  ✗ 转换失败: {e}")
            continue
        
        cleaned, found_refs = remove_references(md)
        print(f"  {'✓ 已移除参考文献' if found_refs else '⚠ 未找到参考文献'}")
        
        output = folder / f"{pdf.stem}.md"
        
        try:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(cleaned)
            print(f"  ✓ 保存: {output.name}")
            success += 1
        except Exception as e:
            print(f"  ✗ 保存失败: {e}")
    
    print("\n" + "-" * 50)
    print(f"\n完成! {success}/{len(pdf_files)} 个文件转换成功")


def main():
    print("=" * 50)
    print("  PDF → Markdown (去除参考文献)")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 获取路径
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        print("\n使用方法:")
        print(f"  python {Path(__file__).name} <PDF文件夹路径>")
        print("\n示例:")
        print(f"  python {Path(__file__).name} ./papers")
        print(f"  python {Path(__file__).name} ~/Documents/论文")
        sys.exit(0)
    
    print(f"\n目标: {folder}")
    process_folder(folder)


if __name__ == "__main__":
    main()
