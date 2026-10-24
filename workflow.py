import re
import subprocess
import sys
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agents import (
    CODING_SYSTEM,
    DESIGN_SYSTEM,
    REQUIREMENT_SYSTEM,
    build_llm,
)
from config import (
    CODE_EXEC_TIMEOUT,
    MAX_FIX_ITERATIONS,
    OUTPUT_DIR,
    WORKSPACE_ROOT,
)


class WorkflowState(TypedDict, total=False):
    requirement: str
    spec: str
    design: str
    code: str
    code_file: str
    test_result: str
    error_feedback: str
    iteration: int
    status: str
    messages: Annotated[list, add_messages]


def _extract_code_block(text: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def _llm_invoke(llm, system: str, user: str) -> str:
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return resp.content


def build_workflow():
    llm = build_llm()

    def analyze_requirement_node(state: WorkflowState) -> dict:
        requirement = state.get("requirement", "")
        spec = _llm_invoke(llm, REQUIREMENT_SYSTEM, f"请分析以下用户需求：\n\n{requirement}")
        return {
            "spec": spec,
            "messages": [
                HumanMessage(content=f"[需求] {requirement}"),
                AIMessage(content="[需求分析 Agent] 已产出需求规格说明"),
            ],
        }

    def design_solution_node(state: WorkflowState) -> dict:
        spec = state.get("spec", "")
        design = _llm_invoke(
            llm, DESIGN_SYSTEM, f"请基于以下需求规格说明，输出技术设计方案：\n\n{spec}"
        )
        return {
            "design": design,
            "messages": [AIMessage(content="[方案设计 Agent] 已产出技术设计方案")],
        }

    def write_code_node(state: WorkflowState) -> dict:
        spec = state.get("spec", "")
        design = state.get("design", "")
        feedback = state.get("error_feedback", "")

        user = f"""# 需求规格说明
{spec}

# 技术设计方案
{design}
"""
        if feedback:
            user += f"""

# 上次验证失败的错误信息（请修复后重新输出完整代码）
{feedback}
"""
        raw = _llm_invoke(llm, CODING_SYSTEM, user)
        code = _extract_code_block(raw)
        return {
            "code": code,
            "messages": [
                AIMessage(
                    content="[代码实现 Agent] 已生成代码" + ("（修复迭代）" if feedback else "")
                )
            ],
        }

    def verify_code_node(state: WorkflowState) -> dict:
        code = state.get("code", "")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        code_file = OUTPUT_DIR / "generated.py"
        code_file.write_text(code, encoding="utf-8")

        try:
            result = subprocess.run(
                [sys.executable, str(code_file)],
                capture_output=True,
                text=True,
                timeout=CODE_EXEC_TIMEOUT,
                cwd=WORKSPACE_ROOT,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            if result.returncode == 0:
                status = "passed"
                test_result = f"运行通过（退出码 0）\n\n[stdout]\n{stdout}"
            else:
                status = "failed"
                test_result = (
                    f"运行失败（退出码 {result.returncode}）\n\n"
                    f"[stdout]\n{stdout}\n\n[stderr]\n{stderr}"
                )
        except subprocess.TimeoutExpired:
            status = "failed"
            test_result = f"运行超时（>{CODE_EXEC_TIMEOUT}s），可能存在死循环或耗时过长。"
        except Exception as e:
            status = "failed"
            test_result = f"执行异常: {e}"

        iteration = state.get("iteration", 0) + 1
        error_feedback = "" if status == "passed" else test_result

        return {
            "code_file": str(code_file),
            "test_result": test_result,
            "error_feedback": error_feedback,
            "iteration": iteration,
            "status": status,
            "messages": [AIMessage(content=f"[自动验证] {status}（第 {iteration} 次）")],
        }

    def route_after_verify(state: WorkflowState) -> str:
        if state.get("status") == "passed":
            return END
        if state.get("iteration", 0) < MAX_FIX_ITERATIONS:
            return "write_code"
        return END

    graph = StateGraph(WorkflowState)
    graph.add_node("analyze_requirement", analyze_requirement_node)
    graph.add_node("design_solution", design_solution_node)
    graph.add_node("write_code", write_code_node)
    graph.add_node("verify_code", verify_code_node)

    graph.add_edge(START, "analyze_requirement")
    graph.add_edge("analyze_requirement", "design_solution")
    graph.add_edge("design_solution", "write_code")
    graph.add_edge("write_code", "verify_code")
    graph.add_conditional_edges(
        "verify_code",
        route_after_verify,
        {"write_code": "write_code", END: END},
    )

    return graph.compile()
