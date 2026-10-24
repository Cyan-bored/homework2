import sys

from workflow import build_workflow

DEMO_REQUIREMENT = (
    "实现一个函数，判断一个正整数是否为质数；"
    "再实现一个函数，返回不超过 n 的所有质数列表。"
)

BANNER = """================================================
   SEWorkflow - Mini SE 流程（3-Agent 协作）
   需求分析 Agent → 方案设计 Agent → 代码实现 Agent
   （代码生成后自动验证，失败自动修复）
================================================
"""


def _print_log(messages) -> None:
    print("\n【执行日志】")
    for msg in messages:
        kind = msg.__class__.__name__
        if kind == "HumanMessage":
            print(f"  · {msg.content}")
        elif kind == "AIMessage":
            print(f"  · {msg.content}")


def _print_report(state: dict) -> None:
    print("\n" + "=" * 60)
    print("  交付报告")
    print("=" * 60)

    print("\n【1. 需求分析（需求分析 Agent 产出）】")
    print(state.get("spec", "(无)"))

    print("\n【2. 方案设计（方案设计 Agent 产出）】")
    print(state.get("design", "(无)"))

    print("\n【3. 生成代码（代码实现 Agent 产出）】")
    print(f"  保存位置: {state.get('code_file', '(未保存)')}")
    print("  代码内容:")
    print("  " + "-" * 50)
    print(state.get("code", "(无)"))
    print("  " + "-" * 50)

    print("\n【4. 自动验证结果】")
    print(f"  状态: {state.get('status', 'unknown')}")
    print(f"  迭代次数: {state.get('iteration', 0)}")
    print(state.get("test_result", "(无)"))


def run(requirement: str, verbose: bool = True) -> dict:
    app = build_workflow()
    initial_state = {"requirement": requirement, "iteration": 0}
    result = app.invoke(initial_state)

    if verbose:
        _print_log(result.get("messages", []))
        _print_report(result)
    return result


def repl() -> None:
    print(BANNER)
    print("  输入 /exit 退出 | 输入 /demo 运行内置示例\n")
    while True:
        try:
            requirement = input("需求: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        if not requirement:
            continue
        if requirement == "/exit":
            print("再见！")
            break
        if requirement == "/demo":
            requirement = DEMO_REQUIREMENT
        try:
            run(requirement)
        except KeyboardInterrupt:
            print("\n(已中断本次执行)")
        except Exception as e:
            print(f"\n[错误] {e}\n(已跳过本次执行，可继续输入需求)")


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--demo":
        run(DEMO_REQUIREMENT)
    elif args:
        run(" ".join(args))
    else:
        repl()


if __name__ == "__main__":
    main()
