#!/usr/bin/env python3
"""
PDF to Markdown Converter for Academic Papers
将学术论文PDF转换为Markdown，并自动去除参考文献部分

改进版：
- 支持单文件和文件夹
- 可指定输出目录
- 递归处理子文件夹
- 保留附录等参考文献后的内容
- 多进程并行加速
- 完整的 CLI 选项
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ============ 配置区域 ============
# 参考文献标题模式
REFERENCE_PATTERNS = [
    r'^#{1,6}\s*References?\s*$',
    r'^References?\s*$',
    r'^\*\*References?\*\*\s*$',
    r'^#{1,6}\s*参考文献\s*$',
    r'^参考文献\s*$',
    r'^#{1,6}\s*Bibliography\s*$',
    r'^Bibliography\s*$',
    r'^#{1,6}\s*REFERENCES?\s*$',
    r'^REFERENCES?\s*$',
    r'^#{1,6}\s*Literature\s+Cited\s*$',
    r'^Literature\s+Cited\s*$',
    r'^#{1,6}\s*Works\s+Cited\s*$',
    r'^Works\s+Cited\s*$',
]

# 需要保留的后续章节（参考文献之后可能出现的）
PRESERVE_PATTERNS = [
    r'^#{1,6}\s*Appendi(?:x|ces)',
    r'^#{1,6}\s*附录',
    r'^#{1,6}\s*Supplementary',
    r'^#{1,6}\s*补充材料',
    r'^#{1,6}\s*Acknowledg(?:e)?ments?',
    r'^#{1,6}\s*致谢',
    r'^#{1,6}\s*Author\s+Contributions?',
    r'^#{1,6}\s*Conflict\s+of\s+Interest',
    r'^#{1,6}\s*Data\s+Availability',
    r'^#{1,6}\s*Code\s+Availability',
    r'^#{1,6}\s*Funding',
    r'^#{1,6}\s*Ethics',
]
# ==================================


@dataclass
class ConversionResult:
    """单个文件的转换结果"""
    path: Path
    success: bool
    output_path: Optional[Path] = None
    refs_removed: bool = False
    error: Optional[str] = None
    time_seconds: float = 0.0
    size_bytes: int = 0


def check_dependencies() -> bool:
    """检查并提示安装依赖"""
    try:
        import pymupdf4llm  # noqa: F401
        return True
    except ImportError:
        print("=" * 50)
        print("  缺少依赖: pymupdf4llm")
        print("=" * 50)
        print("\n请运行以下命令安装:\n")
        
        if sys.platform == "darwin":
            print("  pip3 install --user --break-system-packages pymupdf4llm")
        elif sys.platform == "win32":
            print("  pip install pymupdf4llm")
        else:
            print("  pip3 install --user pymupdf4llm")
        
        print()
        return False


def get_heading_level(line: str) -> int:
    """获取 Markdown 标题级别，非标题返回 0"""
    match = re.match(r'^(#{1,6})\s+', line)
    return len(match.group(1)) if match else 0


def remove_references(md_content: str, keep_refs: bool = False) -> tuple[str, bool]:
    """
    移除参考文献部分，但保留后续的附录等章节
    
    Args:
        md_content: Markdown 内容
        keep_refs: 是否保留参考文献
        
    Returns:
        (处理后的内容, 是否找到并移除了参考文献)
    """
    if keep_refs:
        return md_content, False
    
    lines = md_content.split('\n')
    result_lines: list[str] = []
    ref_start_idx: Optional[int] = None
    ref_heading_level: int = 0
    
    # 第一遍：找到参考文献开始位置
    for i, line in enumerate(lines):
        stripped = line.strip()
        for pattern in REFERENCE_PATTERNS:
            if re.match(pattern, stripped, re.IGNORECASE):
                ref_start_idx = i
                ref_heading_level = get_heading_level(stripped)
                # 如果不是 Markdown 标题格式，假设为顶级
                if ref_heading_level == 0:
                    ref_heading_level = 1
                break
        if ref_start_idx is not None:
            break
    
    # 没找到参考文献，原样返回
    if ref_start_idx is None:
        return md_content, False
    
    # 第二遍：找到需要保留的后续章节
    preserve_start_idx: Optional[int] = None
    
    for i in range(ref_start_idx + 1, len(lines)):
        stripped = lines[i].strip()
        current_level = get_heading_level(stripped)
        
        # 检查是否是同级或更高级别的标题（可能是新章节）
        if current_level > 0 and current_level <= ref_heading_level:
            # 检查是否匹配需要保留的模式
            for pattern in PRESERVE_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    preserve_start_idx = i
                    break
            if preserve_start_idx is not None:
                break
    
    # 组合结果
    result_lines = lines[:ref_start_idx]
    
    # 如果有需要保留的后续内容
    if preserve_start_idx is not None:
        # 添加空行分隔
        result_lines.append('')
        result_lines.extend(lines[preserve_start_idx:])
    
    # 移除末尾多余空行
    while result_lines and result_lines[-1].strip() == '':
        result_lines.pop()
    
    return '\n'.join(result_lines), True


def convert_single_pdf(
    pdf_path: Path,
    output_dir: Optional[Path],
    keep_refs: bool,
    verbose: bool
) -> ConversionResult:
    """
    转换单个 PDF 文件
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录（None 则输出到原目录）
        keep_refs: 是否保留参考文献
        verbose: 详细输出
    """
    start_time = time.time()
    
    try:
        import pymupdf4llm
    except ImportError:
        return ConversionResult(
            path=pdf_path,
            success=False,
            error="pymupdf4llm 未安装"
        )
    
    try:
        # 转换 PDF
        md_content = pymupdf4llm.to_markdown(str(pdf_path))
        
        # 处理参考文献
        cleaned, refs_removed = remove_references(md_content, keep_refs)
        
        # 确定输出路径
        if output_dir:
            out_path = output_dir / f"{pdf_path.stem}.md"
        else:
            out_path = pdf_path.parent / f"{pdf_path.stem}.md"
        
        # 保存文件
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        
        elapsed = time.time() - start_time
        
        return ConversionResult(
            path=pdf_path,
            success=True,
            output_path=out_path,
            refs_removed=refs_removed,
            time_seconds=elapsed,
            size_bytes=pdf_path.stat().st_size
        )
        
    except Exception as e:
        return ConversionResult(
            path=pdf_path,
            success=False,
            error=str(e),
            time_seconds=time.time() - start_time
        )


def find_pdf_files(path: Path, recursive: bool) -> list[Path]:
    """查找 PDF 文件"""
    if path.is_file():
        if path.suffix.lower() == '.pdf':
            return [path]
        return []
    
    if recursive:
        return list(path.rglob("*.[pP][dD][fF]"))
    else:
        return list(path.glob("*.[pP][dD][fF]"))


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def process_files(
    input_path: Path,
    output_dir: Optional[Path],
    recursive: bool,
    keep_refs: bool,
    dry_run: bool,
    verbose: bool,
    workers: int
) -> None:
    """处理文件（主流程）"""
    
    # 查找 PDF 文件
    pdf_files = find_pdf_files(input_path, recursive)
    
    if not pdf_files:
        print(f"✗ 未找到 PDF 文件: {input_path}")
        sys.exit(1)
    
    print(f"\n找到 {len(pdf_files)} 个 PDF 文件")
    
    if dry_run:
        print("\n[预览模式] 将处理以下文件：")
        for pdf in pdf_files:
            out_dir = output_dir or pdf.parent
            print(f"  {pdf} → {out_dir / (pdf.stem + '.md')}")
        return
    
    print("-" * 60)
    
    results: list[ConversionResult] = []
    total_start = time.time()
    
    # 单文件直接处理，多文件使用进程池
    if len(pdf_files) == 1:
        result = convert_single_pdf(pdf_files[0], output_dir, keep_refs, verbose)
        results.append(result)
        _print_result(result, 1, 1, verbose)
    else:
        # 多进程处理
        effective_workers = min(workers, len(pdf_files))
        
        with ProcessPoolExecutor(max_workers=effective_workers) as executor:
            futures = {
                executor.submit(
                    convert_single_pdf, pdf, output_dir, keep_refs, verbose
                ): pdf for pdf in pdf_files
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                results.append(result)
                _print_result(result, i, len(pdf_files), verbose)
    
    # 统计信息
    total_time = time.time() - total_start
    _print_summary(results, total_time)


def _print_result(result: ConversionResult, idx: int, total: int, verbose: bool) -> None:
    """打印单个结果"""
    prefix = f"[{idx}/{total}]"
    
    if result.success:
        ref_status = "✓ 已移除参考文献" if result.refs_removed else "⚠ 未找到参考文献"
        print(f"\n{prefix} {result.path.name}")
        print(f"  {ref_status}")
        if verbose:
            print(f"  大小: {format_size(result.size_bytes)}, 耗时: {result.time_seconds:.2f}s")
        print(f"  ✓ 保存: {result.output_path}")
    else:
        print(f"\n{prefix} {result.path.name}")
        print(f"  ✗ 失败: {result.error}")


def _print_summary(results: list[ConversionResult], total_time: float) -> None:
    """打印汇总信息"""
    success_count = sum(1 for r in results if r.success)
    refs_removed_count = sum(1 for r in results if r.refs_removed)
    total_size = sum(r.size_bytes for r in results if r.success)
    
    print("\n" + "=" * 60)
    print("汇总统计")
    print("=" * 60)
    print(f"  转换成功: {success_count}/{len(results)}")
    print(f"  移除参考文献: {refs_removed_count}/{success_count}")
    print(f"  处理总大小: {format_size(total_size)}")
    print(f"  总耗时: {total_time:.2f}s")
    
    if success_count > 0:
        avg_time = sum(r.time_seconds for r in results if r.success) / success_count
        print(f"  平均每文件: {avg_time:.2f}s")
    
    # 显示失败的文件
    failed = [r for r in results if not r.success]
    if failed:
        print(f"\n失败文件 ({len(failed)}):")
        for r in failed:
            print(f"  ✗ {r.path.name}: {r.error}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF → Markdown 转换器（去除参考文献）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s paper.pdf                    # 转换单个文件
  %(prog)s ./papers                     # 转换文件夹
  %(prog)s ./papers -o ./output         # 指定输出目录
  %(prog)s ./papers -r                  # 递归处理子文件夹
  %(prog)s ./papers --keep-refs         # 保留参考文献
  %(prog)s ./papers --dry-run           # 预览模式
  %(prog)s ./papers -w 4                # 使用 4 个进程并行
        """
    )
    
    parser.add_argument(
        "input",
        type=Path,
        help="PDF 文件或文件夹路径"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="输出目录（默认：与输入文件同目录）"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="递归处理子文件夹"
    )
    parser.add_argument(
        "--keep-refs",
        action="store_true",
        help="保留参考文献（不删除）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际转换"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细信息"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="并行处理的进程数（默认：4）"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  PDF → Markdown (去除参考文献)")
    print("=" * 60)
    
    # 检查依赖
    if not args.dry_run and not check_dependencies():
        sys.exit(1)
    
    # 验证输入路径
    if not args.input.exists():
        print(f"\n✗ 路径不存在: {args.input}")
        sys.exit(1)
    
    # 创建输出目录
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    
    print(f"\n输入: {args.input}")
    if args.output:
        print(f"输出: {args.output}")
    if args.recursive:
        print("模式: 递归")
    if args.keep_refs:
        print("选项: 保留参考文献")
    
    process_files(
        input_path=args.input,
        output_dir=args.output,
        recursive=args.recursive,
        keep_refs=args.keep_refs,
        dry_run=args.dry_run,
        verbose=args.verbose,
        workers=args.workers
    )


if __name__ == "__main__":
    main()
