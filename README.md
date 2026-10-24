# SEWorkflow — Mini SE 流程（3-Agent 协作 Workflow）

一个基于 **LangChain + LangGraph** 的简单 Workflow MVP，用三个专业化 Agent 协作完成 **需求 → 设计 → 代码 → 自动验证** 的完整流程，用于理解 Workflow 编排、Agent 间通信、状态管理、条件分支与循环等核心概念。

## 一、项目亮点

| 能力 | 说明 |
|------|------|
| 多 Agent 协作 | 需求分析、方案设计、代码实现 3 个 Agent 顺序协作 |
| 消息传递 / 状态共享 | 所有 Agent 读写同一个 `WorkflowState`，产出物通过共享状态在节点间传递 |
| 顺序执行 | 需求 → 设计 → 代码 → 验证 单向推进（基本流程控制） |
| 条件分支 + 循环 | 代码验证失败时，带错误反馈自动回到编码 Agent 修复（最多 N 次） |
| 错误恢复 | 验证失败不中断流程，而是把错误信息作为反馈驱动自修复 |
| 执行日志 | 完整记录每个 Agent 的动作，可视化协作过程 |

## 二、工作流程图

```
用户需求
   │
   ▼
┌──────────────┐
│ 需求分析 Agent │  requirement → spec
└──────┬───────┘
       ▼
┌──────────────┐
│ 方案设计 Agent │  spec → design
└──────┬───────┘
       ▼
┌──────────────┐
│ 代码实现 Agent │  spec + design (+ 错误反馈) → code
└──────┬───────┘
       ▼
┌──────────────┐
│ 自动验证节点   │  运行生成的代码 → 通过 / 失败
└──────┬───────┘
       │ 失败且未达上限 ──▶ 回到「代码实现 Agent」（修复循环）
       │ 通过或达上限 ────▶ END
       ▼
      END
```

## 三、快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 LLM API

复制 `.env.example` 为 `.env`，填入你的 API Key（兼容任意 OpenAI 协议服务商）：

```bash
# DeepSeek 示例
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

### 3. 运行

```bash
# 单次执行一个需求
python main.py "实现一个函数判断正整数是否为质数，并列出不超过 n 的所有质数"

# 运行内置示例
python main.py --demo

# 交互模式（循环输入需求）
python main.py
```

## 四、运行示例

```
$ python main.py --demo

【执行日志】
  · [需求] 实现一个函数，判断一个正整数是否为质数...
  · [需求分析 Agent] 已产出需求规格说明
  · [方案设计 Agent] 已产出技术设计方案
  · [代码实现 Agent] 已生成代码
  · [自动验证] passed（第 1 次）

============================================================
  交付报告
============================================================

【1. 需求分析（需求分析 Agent 产出）】
## 需求规格说明
### 1. 功能目标
...

【2. 方案设计（方案设计 Agent 产出）】
## 技术设计方案
...

【3. 生成代码（代码实现 Agent 产出）】
  保存位置: output\generated.py
  代码内容:
  ...

【4. 自动验证结果】
  状态: passed
  迭代次数: 1
  运行通过（退出码 0）
  ...
```

## 五、项目结构

```
SEWorkflow/
├── main.py            # 命令行入口（单次 / 交互 / --demo），打印执行日志与交付报告
├── workflow.py        # Workflow 编排：LangGraph StateGraph（节点 + 边 + 条件路由）
├── agents.py          # 三个专业化 Agent 的 Prompt 与 LLM 构建
├── tools.py           # 工具集（复用项目1：python_execute / read_file / list_files / search_code）
├── config.py          # 配置层（.env 加载，复用项目1并新增 Workflow 参数）
├── output/            # 生成代码的保存目录（运行后自动创建）
├── requirements.txt   # Python 依赖
├── README.md          # 项目说明（本文件）
├── Design.md          # 设计文档
└── .env.example       # 环境变量模板
```

## 六、常见问题

- **启动报「未检测到 OPENAI_API_KEY」**：请先复制 `.env.example` 为 `.env` 并填入 API Key。
- **生成的代码在哪**：保存在 `output/generated.py`，可直接查看或单独运行。
- **想调整自动修复次数**：在 `.env` 中设置 `MAX_FIX_ITERATIONS`（默认 3）。
