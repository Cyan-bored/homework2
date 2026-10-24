import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool

from config import CODE_EXEC_TIMEOUT, WORKSPACE_ROOT


def _safe_path(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = WORKSPACE_ROOT / p
    p = p.resolve()
    if WORKSPACE_ROOT not in p.parents and p != WORKSPACE_ROOT:
        raise ValueError(f"禁止访问工作区之外的路径: {p}（工作区: {WORKSPACE_ROOT}）")
    return p


@tool
def python_execute(code: str) -> str:
    """执行一段 Python 代码并返回 stdout/stderr 结果。

    用于验证 Agent 生成的代码、运行测试用例、检查代码行为。
    Args:
        code: 要执行的 Python 源代码。
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=CODE_EXEC_TIMEOUT,
            cwd=WORKSPACE_ROOT,
        )
        output = result.stdout
        if result.returncode != 0:
            output += f"\n[退出码 {result.returncode}] {result.stderr.strip()}"
        return output.strip() or "(无输出)"
    except subprocess.TimeoutExpired:
        return f"[错误] 代码执行超时（>{CODE_EXEC_TIMEOUT}s），请优化代码或缩短运行时间。"
    except Exception as e:
        return f"[错误] 执行失败: {e}"


@tool
def read_file(file_path: str) -> str:
    """读取指定文本文件的内容。

    Args:
        file_path: 文件路径（相对工作区或绝对路径）。
    """
    try:
        path = _safe_path(file_path)
        if not path.is_file():
            return f"[错误] 文件不存在: {file_path}"
        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) > 20000:
            content = content[:20000] + "\n...(文件过长，已截断)"
        return content or "(空文件)"
    except ValueError as e:
        return f"[错误] {e}"
    except Exception as e:
        return f"[错误] 读取失败: {e}"


@tool
def list_files(dir_path: str = ".") -> str:
    """列出指定目录下的文件和子目录，帮助了解项目结构。

    Args:
        dir_path: 目录路径，默认为工作区根目录。
    """
    try:
        path = _safe_path(dir_path)
        if not path.is_dir():
            return f"[错误] 目录不存在: {dir_path}"
        entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        lines = []
        for entry in entries:
            if entry.is_dir():
                lines.append(f"[目录] {entry.name}/")
            else:
                lines.append(f"[文件] {entry.name} ({entry.stat().st_size} bytes)")
        return "\n".join(lines) if lines else "(空目录)"
    except ValueError as e:
        return f"[错误] {e}"
    except Exception as e:
        return f"[错误] 列目录失败: {e}"


@tool
def search_code(keyword: str, file_glob: str = "**/*.py") -> str:
    """在代码库中搜索包含指定关键字的代码行。

    Args:
        keyword: 要搜索的关键字（函数名/类名/任意字符串）。
        file_glob: 文件匹配模式，默认只搜索 Python 文件。
    """
    try:
        matches = []
        for path in WORKSPACE_ROOT.glob(file_glob):
            if any(part in {".git", "__pycache__", "node_modules", ".venv"}
                   for part in path.parts):
                continue
            if not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for no, line in enumerate(lines, 1):
                if keyword in line:
                    rel = path.relative_to(WORKSPACE_ROOT)
                    matches.append(f"{rel}:{no}: {line.strip()}")
                    if len(matches) >= 50:
                        return "\n".join(matches) + "\n...(结果过多，已截断)"
        return "\n".join(matches) if matches else f"未找到包含 '{keyword}' 的代码。"
    except Exception as e:
        return f"[错误] 搜索失败: {e}"


ALL_TOOLS = [python_execute, read_file, list_files, search_code]
