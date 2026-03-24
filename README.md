# RPGLE 可视化套件 (RPGLE Visualization Suite)

AS400 RPGLE 代码的**可视化**解决方案 —— 将你的 RPGLE 代码转化为流程图、架构图和 SDD 文档。

## 🎯 核心功能

| 组件 | 功能 | 目的 |
|------|------|------|
| **rpgle-flowchart** | RPGLE 代码 → 流程图 | 可视化程序逻辑 |
| **rpgle-sdd** | 需求 → SDD 文档 | 标准化需求分析 |
| **as400-analyzer** | 程序血缘分析 | 理解系统架构 |

## 📦 组件详情

### 1. rpgle-flowchart
将 RPGLE 代码转换为多格式流程图：
- **Mermaid** - 轻量级图表，适合嵌入文档
- **PlantUML** - 企业级图表，支持复杂架构
- **HTML** - 交互式可视化网页
- **JSON** - 机器可读的中间格式

支持：
- 固定格式 RPGLE
- 自由格式 RPGLE
- SQLRPGLE (EXEC SQL 块)

### 2. rpgle-sdd
软件需求说明书生成器：
- 启发式需求分析
- Jira/Confluence 集成
- 自动测试用例生成
- 影响分析（血缘集成）

### 3. as400-analyzer
程序血缘分析工具：
- 调用关系图
- 文件依赖分析
- 影响范围评估

## 🚀 快速开始

```bash
# 安装
pip install -e rpgle_flowchart
pip install -e rpgle_sdd
pip install -e as400_analyzer

# 生成流程图 (Mermaid)
python -m rpgle_flowchart.rpgle_flowchart your_program.rpgle --format mermaid

# 生成流程图 (HTML)
python -m rpgle_flowchart.rpgle_flowchart your_program.rpgle --format html --output viz.html

# 生成 SDD
python -m rpgle_sdd.sdd_generator --interactive

# 血缘分析
python -m as400_analyzer.analyzer --program PROGRAM001 --血缘
```

## 📁 项目结构

```
rpgle-viz-suite/
├── rpgle_flowchart/       # 流程图生成器
│   ├── rpgle_flowchart.py
│   └── references/         # 模式参考、样式指南
├── rpgle_sdd/             # SDD 文档生成器
│   ├── sdd_generator.py
│   └── references/        # 模板、启发式问题
├── as400_analyzer/        # 血缘分析器
│   └── analyzer.py
├── integration/           # 集成模块
├── tests/                # 单元测试
├── sample_code/          # 示例代码
└── docs/                 # 文档
```

## 🔌 集成示例

### 与现有系统集成
```python
from rpgle_flowchart import FlowchartGenerator
from rpgle_sdd import SDDGenerator
from as400_analyzer import ProgramAnalyzer

# 1. 分析程序血缘
analyzer = ProgramAnalyzer()
dependencies = analyzer.analyze('PROGRAM001')

# 2. 生成流程图
flowchart = FlowchartGenerator()
diagram = flowchart.generate(dependencies['main_program'], format='mermaid')

# 3. 生成 SDD
sdd = SDDGenerator()
doc = sdd.generate(dependencies['programs'], format='markdown')
```

## 📊 可视化示例

### Mermaid 流程图
\`\`\`mermaid
graph TD
    A[START] --> B{条件判断}
    B -->|是| C[处理]
    B -->|否| D[异常处理]
    C --> E[输出]
    D --> E
\`\`\`

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
