# 快速开始指南

## 安装

```bash
git clone https://github.com/noOne-Oliver/rpgle-viz-suite.git
cd rpgle-viz-suite
pip install -e .
```

## 使用示例

### 1. 生成流程图

```python
from rpgle_flowchart import FlowchartGenerator

code = '''
     D Var1            S             10A
      /free
        if Var1 = 'A';
          Var1 = 'B';
        endif;
      /end-free
'''

gen = FlowchartGenerator()
print(gen.generate(code, format='mermaid'))
```

### 2. 生成 SDD 文档

```python
from rpgle_sdd import SDDGenerator

sdd = SDDGenerator()
doc = sdd.generate({'name': 'PROGRAM001', 'description': 'Test program'})
print(doc)
```

### 3. 血缘分析

```python
from as400_analyzer import ProgramAnalyzer

analyzer = ProgramAnalyzer()
result = analyzer.analyze('PROGRAM001')
print(result)
```

## 输出格式

| 格式 | 用途 |
|------|------|
| mermaid | 轻量级图表，嵌入 Markdown |
| plantuml | 企业级图表 |
| html | 交互式网页 |
| json | 程序间数据交换 |
