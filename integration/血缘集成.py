# -*- coding: utf-8 -*-
"""
血缘集成 - Program Lineage Integration
连接 as400-analyzer 与其他组件
"""

from typing import Dict, Any, List, Optional


class 血缘集成器:
    """程序血缘分析集成器"""

    def __init__(self):
        self._analyzer = None

    def _get_analyzer(self):
        """延迟加载分析器"""
        if self._analyzer is None:
            try:
                from as400_analyzer.analyzer import ProgramAnalyzer
                self._analyzer = ProgramAnalyzer()
            except ImportError:
                self._analyzer = None
        return self._analyzer

    def 分析血缘(
        self,
        program_name: str,
        depth: int = 3
    ) -> Dict[str, Any]:
        """
        分析程序血缘关系

        Args:
            program_name: 程序名称
            depth: 追溯深度

        Returns:
            血缘分析结果
        """
        analyzer = self._get_analyzer()

        if analyzer:
            return analyzer.analyze(program_name, depth=depth)
        else:
            # 基础实现
            return {
                'program': program_name,
                'calls': [],
                'called_by': [],
                'files': [],
                'depth': depth
            }

    def 生成血缘图(
        self,
        program_name: str,
        format: str = 'mermaid'
    ) -> str:
        """
        生成血缘关系图

        Args:
            program_name: 程序名称
            format: 输出格式 (mermaid|plantuml|json)

        Returns:
            血缘图内容
        """
        lineage = self.分析血缘(program_name)

        if format == 'mermaid':
            return self._to_mermaid(lineage)
        elif format == 'plantuml':
            return self._to_plantuml(lineage)
        elif format == 'json':
            import json
            return json.dumps(lineage, indent=2, ensure_ascii=False)
        return str(lineage)

    def _to_mermaid(self, lineage: Dict) -> str:
        """转换为Mermaid格式"""
        lines = ['```mermaid', 'graph TD']

        # 添加节点
        prog = lineage.get('program', 'UNKNOWN')
        lines.append(f'    {prog}[({prog})]')

        for called in lineage.get('calls', []):
            lines.append(f'    {prog} --> {called}')
            lines.append(f'    {called}[({called})]')

        for caller in lineage.get('called_by', []):
            lines.append(f'    {caller} --> {prog}')

        lines.append('```')
        return '\n'.join(lines)

    def _to_plantuml(self, lineage: Dict) -> str:
        """转换为PlantUML格式"""
        lines = ['@startuml']

        prog = lineage.get('program', 'UNKNOWN')
        lines.append(f'node "{prog}" as {prog}')

        for called in lineage.get('calls', []):
            lines.append(f'"{prog}" --> "{called}"')

        for caller in lineage.get('called_by', []):
            lines.append(f'"{caller}" --> "{prog}"')

        lines.append('@enduml')
        return '\n'.join(lines)

    def 批量分析(
        self,
        program_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """批量分析多个程序"""
        results = {}
        for name in program_names:
            results[name] = self.分析血缘(name)
        return results
