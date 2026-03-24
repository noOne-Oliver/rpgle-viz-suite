# -*- coding: utf-8 -*-
"""
Flowchart Integration - 流程图集成器
统一入口，调用 rpgle-flowchart 生成可视化
"""

import json
from typing import Optional, Dict, Any


class Flowchart集成器:
    """流程图生成集成器"""

    def __init__(self, default_format: str = 'mermaid'):
        self.default_format = default_format
        self._flowchart_gen = None

    def _get_generator(self):
        """延迟加载流程图生成器"""
        if self._flowchart_gen is None:
            try:
                from rpgle_flowchart.rpgle_flowchart import FlowchartGenerator
                self._flowchart_gen = FlowchartGenerator()
            except ImportError:
                # 备用：直接实现
                self._flowchart_gen = None
        return self._flowchart_gen

    def 生成流程图(
        self,
        code: str,
        format: str = 'mermaid',
        output_path: Optional[str] = None
    ) -> str:
        """
        生成流程图

        Args:
            code: RPGLE 代码
            format: 输出格式 (mermaid|plantuml|html|json)
            output_path: 输出文件路径

        Returns:
            流程图内容
        """
        gen = self._get_generator()

        if gen:
            result = gen.generate(code, format=format)
        else:
            # 基础实现
            result = self._basic_generate(code, format)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)

        return result

    def _basic_generate(self, code: str, format: str) -> str:
        """基础流程图生成（当模块不可用时）"""
        lines = code.split('\n')
        nodes = []
        edges = []

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('C') and ('IF' in line or 'IF' in line.upper()):
                nodes.append(f'    N{i}[{line[:30]}...]')
            elif line.startswith('D') and 'END' in line.upper():
                pass

        if format == 'mermaid':
            result = '```mermaid\ngraph TD\n'
            result += '\n'.join(nodes) + '\n'
            result += '```'
            return result
        elif format == 'json':
            return json.dumps({'nodes': nodes, 'edges': edges}, indent=2)
        return str(nodes)

    def 批量生成(
        self,
        code_dict: Dict[str, str],
        format: str = 'mermaid',
        output_dir: str = './flowcharts'
    ) -> Dict[str, str]:
        """批量生成流程图"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        results = {}
        for name, code in code_dict.items():
            output_path = f'{output_dir}/{name}.{format}'
            results[name] = self.生成流程图(code, format, output_path)

        return results
