# Design.md — SEWorkflow 设计文档

## 1. 项目目标

搭建一个 **3 个 Agent 协作的 Simple Workflow MVP**，跑通「需求分析 → 方案设计 → 代码实现 → 自动验证」的端到端流程，理解并实践以下核心概念：

- **Workflow 编排**：用 LangGraph `StateGraph` 显式定义节点（Agent）与边（控制流）。
- **Agent 间通信**：通过共享状态（`WorkflowState`）在节点间传递产出物。
- **状态管理**：单一状态对象贯穿全流程，可观测、可持久化（可扩展 checkpointer）。
- **流程控制**：顺序执行 + 条件分支 + 循环（验证失败自动修复）。

## 2. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | LangChain 生态最成熟 |
| 编排框架 | LangGraph `StateGraph` | 把 Workflow 表达为显式状态图，节点/边可定制，天然支持条件路由与状态持久化 |
| Agent 实现 | `ChatOpenAI` + 角色化 Prompt | 三个 Agent 复用同一 LLM 接入，仅靠 System Prompt 区分角色（需求分析师/架构师/工程师） |
| LLM 接入 | `langchain-openai` | 兼容 OpenAI 协议，可无缝切换 DeepSeek / 通义千问 / OpenAI |
| 工具 | 复用项目1 的 `tools.py` | `python_execute` / `read_file` / `list_files` / `search_code`，含路径安全与超时防护 |
| 配置 | `python-dotenv` | `.env` 集中管理 API Key 与 Workflow 参数，改配置不改代码 |

## 3. 架构设计

### 3.1 总体架构

```
┌─────────────────────────────────────────────────────┐
│                 LangGraph StateGraph                 │
│                                                     │
│   ┌──────────┐  spec   ┌──────────┐  design  ┌──────────┐  code  ┌──────────┐
│   │ 需求分析  │ ──────▶ │ 方案设计  │ ───────▶ │ 代码实现  │ ──────▶ │ 自动验证  │
│   │  Agent   │         │  Agent   │          │  Agent   │        │  节点    │
│   └──────────┘         └──────────┘          └──────────┘        └────┬─────┘
│        ▲                                     ▲ 修复反馈(error_feedback)│
│        └─────────────────────────────────────┘                       │
│                                             验证失败且未达上限时循环返回  │
│                                                                     │
│                     WorkflowState（共享状态）                          │
└─────────────────────────────────────────────────────┘
```

### 3.2 状态设计（Agent 间消息传递 / 状态共享）

所有节点读写同一个 `WorkflowState`（`TypedDict`），这是本项目「Agent 间通信」的实现方式：

| 字段 | 含义 | 由谁写入 |
|------|------|----------|
| `requirement` | 用户原始需求 | 初始状态 |
| `spec` | 需求规格说明 | 需求分析 Agent |
| `design` | 技术设计方案 | 方案设计 Agent |
| `code` | 生成的代码 | 代码实现 Agent |
| `code_file` | 代码保存路径 | 自动验证节点 |
| `test_result` | 验证结果 | 自动验证节点 |
| `error_feedback` | 修复反馈 | 自动验证节点（失败时） |
| `iteration` | 修复迭代次数 | 自动验证节点 |
| `status` | `passed` / `failed` | 自动验证节点 |
| `messages` | 执行日志（`add_messages` 累积） | 所有节点 |

### 3.3 三个 Agent 的职责与 Prompt 设计

每个 Agent 复用同一 `build_llm()`，仅 System Prompt 不同，实现角色分离：

| Agent | 角色 | 输入 | 输出 | Prompt 要点 |
|-------|------|------|------|-------------|
| 需求分析 | 产品需求分析师 | `requirement` | `spec` | 强制输出「功能目标 / 功能点 / 输入输出 / 约束」四段式规格 |
| 方案设计 | 软件架构师 | `spec` | `design` | 强制输出「总体思路 / 函数设计 / 数据结构 / 算法 / 验证方式」 |
| 代码实现 | Python 工程师 | `spec`+`design`(+`error_feedback`) | `code` | 要求完整自包含脚本、含 `__main__` 演示、含 `assert` 自测 |

### 3.4 流程控制

1. **顺序执行**（基本要求）：`START → 需求分析 → 方案设计 → 代码实现 → 自动验证`。
2. **条件分支 + 循环**（推荐实现）：自动验证后由 `route_after_verify` 判断：
   - 验证通过 → `END`；
   - 验证失败且 `iteration < MAX_FIX_ITERATIONS` → 回到「代码实现」节点，携带 `error_feedback` 修复；
   - 验证失败且达到上限 → `END`（不无限循环）。
3. **错误恢复**：验证失败不抛异常中断，而是把 stdout/stderr 作为反馈回传，驱动 Agent 自修复。

### 3.5 复用项目 1 的部分

| 模块 | 复用方式 |
|------|----------|
| `config.py` | 复用配置层（.env 加载、LLM 参数），新增 `OUTPUT_DIR`、`MAX_FIX_ITERATIONS` |
| `tools.py` | 原样复用 4 个工具及路径安全校验，供验证节点与后续扩展使用 |
| LLM 接入 | 复用 `ChatOpenAI` + `temperature=0` + `max_retries` + `timeout` 的健壮性模式 |
| 错误处理思想 | 延续「错误信息返回给 Agent 自纠」的设计哲学 |

## 4. 模块划分

```
config.py    → 配置层：.env 加载、参数集中管理（复用项目1）
tools.py     → 能力层：4 个 @tool + 路径安全（复用项目1）
agents.py    → Agent 层：3 个角色化 System Prompt + build_llm()
workflow.py  → 编排层：StateGraph 节点/边/条件路由
main.py      → 交互层：CLI 入口、执行日志与交付报告
```

依赖方向：`main.py → workflow.py → agents.py → tools.py/config.py`，单向无环。

## 5. 边界情况考虑

- 未配置 API Key：启动时给出明确指引并退出（`config.py`）。
- 生成的代码无法运行/死循环：`verify_code` 用子进程 + 超时保护，失败进入修复循环，超限后停止。
- LLM 输出不规范（非纯代码块）：`_extract_code_block` 容错提取，退化为整段文本。
- 修复无限循环：`MAX_FIX_ITERATIONS` 上限强制终止。

## 6. 可扩展方向

- **可视化编排界面**：LangGraph 图结构本身可序列化，可导出图并接入前端可视化。
- **并行执行**：如「需求分析」和「竞品调研」可并行，用 `graph.add_edge(START, ["a", "b"])` 分叉。
- **新增 Agent**：在图中 `add_node` + `add_edge` 即可插入新环节（如代码审查 Agent），复用项目1 的审查能力。
- **持久化状态**：挂载 `checkpointer`（如 `SqliteSaver`），实现跨会话状态恢复与断点续跑。
- **审查节点**：在验证后插入「代码审查 Agent」，用项目1 的 `read_file` + 审查 Prompt 产出改进建议，形成更完整的 SE 闭环。
