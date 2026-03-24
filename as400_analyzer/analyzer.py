#!/usr/bin/env python3
"""
AS400 Program Analyzer - 核心解析引擎 v2.0
支持 RPGLE, RPG, CL, DDS 等文件格式的代码解析
增强功能：
- 字段赋值追踪 (field-values)
- 间接调用分析 (indirect-chain)
- 更完整的血缘图谱
"""

import re
import os
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Union
from enum import Enum
from collections import defaultdict

class SourceType(Enum):
    RPGLE = "rpgle"
    RPG = "rpg"
    CL = "cl"
    CLLE = "clle"
    DDS = "dds"
    PF = "pf"
    LF = "lf"
    SQL = "sql"
    COBOL = "cobol"
    UNKNOWN = "unknown"

@dataclass
class FileReference:
    """文件引用"""
    file_name: str
    program_name: str = ""
    line_number: int = 0
    operation: str = ""  # CHAIN, READ, WRITE, UPDATE, DELETE, EXFMT
    record_name: str = ""

@dataclass
class FieldReference:
    """字段引用"""
    field_name: str
    file_name: str = ""
    program_name: str = ""
    line_number: int = 0
    operation: str = ""
    context: str = ""  # EVAL, CHAIN, KLIST, DS
    is_key: bool = False

@dataclass
class CallReference:
    """程序调用引用"""
    called_program: str
    calling_program: str = ""
    line_number: int = 0
    call_type: str = "CALL"  # CALL, CALLB, SBMJOB, CRTPGM, TRAP

@dataclass
class FieldWrite:
    """字段赋值"""
    field_name: str
    file_name: str = ""
    program_name: str = ""
    line_number: int = 0
    value_source: str = ""  # 赋值的来源表达式
    operation: str = ""  # EVAL, CHAIN后EVAL, WRITE, UPDATE, SET
    raw_code: str = ""  # 原始代码行

@dataclass
class IndirectCall:
    """间接调用"""
    target: str
    call_type: str  # SBMJOB, BNDDIR, CPP, TRIGGER, DATAAREA, DTAQ
    program_name: str = ""
    line_number: int = 0
    details: str = ""

@dataclass
class ProgramInfo:
    """程序信息"""
    name: str
    source_type: SourceType
    description: str = ""
    input_files: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    called_programs: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)
    file_refs: List[FileReference] = field(default_factory=list)
    field_refs: List[FieldReference] = field(default_factory=list)
    call_refs: List[CallReference] = field(default_factory=list)
    field_writes: List[FieldWrite] = field(default_factory=list)
    indirect_calls: List[IndirectCall] = field(default_factory=list)
    lines: int = 0
    path: str = ""

@dataclass
class FieldValueSource:
    """字段赋值来源"""
    program_name: str
    line_number: int
    operation: str  # EVAL, CHAIN+EVAL, WRITE, UPDATE
    value_expression: str
    source_type: str  # CONSTANT, FIELD, EXPRESSION, DB
    path: str = ""

@dataclass
class LineageReport:
    """血缘分析报告"""
    program_name: str
    file_usage: List[str]
    field_usage: Dict[str, List[str]]  # file.field -> [programs]
    upstream: List[Dict]
    downstream: List[Dict]
    field_writes: List[FieldValueSource]
    indirect_calls: List[IndirectCall]


class AS400Parser:
    """AS400 代码解析器"""

    def __init__(self):
        self.source_type_handlers = {
            SourceType.RPGLE: self._parse_rpgle,
            SourceType.RPG: self._parse_rpg,
            SourceType.CL: self._parse_cl,
            SourceType.CLLE: self._parse_cl,
            SourceType.DDS: self._parse_dds,
            SourceType.PF: self._parse_dds,
            SourceType.LF: self._parse_dds,
        }

    def detect_source_type(self, file_path: str) -> SourceType:
        """检测源码类型"""
        ext = os.path.splitext(file_path.lower())[1]
        name = os.path.basename(file_path).upper()

        if ext in ['.rpgle', '.sqlrpgle']:
            return SourceType.RPGLE
        elif ext in ['.rpg', '.sqlrpg']:
            return SourceType.RPG
        elif ext == '.clle':
            return SourceType.CLLE
        elif ext in ['.cl']:
            return SourceType.CL
        elif ext in ['.dds']:
            return SourceType.DDS
        elif name.endswith('.PF') or re.search(r'\.PF$', name):
            return SourceType.PF
        elif name.endswith('.LF') or re.search(r'\.LF$', name):
            return SourceType.LF
        elif ext in ['.sql', '.ddl']:
            return SourceType.SQL
        elif ext in ['.cbl', '.cob']:
            return SourceType.COBOL
        return SourceType.UNKNOWN

    def parse_file(self, file_path: str) -> ProgramInfo:
        """解析 AS400 源码文件"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        source_type = self.detect_source_type(file_path)
        program_name = os.path.splitext(os.path.basename(file_path))[0].upper()

        if source_type in self.source_type_handlers:
            return self.source_type_handlers[source_type](content, program_name, file_path)

        return self._parse_generic(content, program_name, file_path, source_type)

    def _parse_rpgle(self, content: str, program_name: str, file_path: str) -> ProgramInfo:
        """解析自由格式 RPGLE"""
        info = ProgramInfo(name=program_name, source_type=SourceType.RPGLE, path=file_path)
        lines = content.split('\n')

        # 提取描述
        for line in lines[:10]:
            stripped = line.strip()
            if stripped.startswith('**') or '====' in line:
                info.description = stripped.strip('*').strip('=').strip()
                if len(info.description) > 100:
                    info.description = info.description[:100] + '...'
                break
            # 处理自由格式注释
            if stripped.startswith('//'):
                info.description = stripped.strip('/').strip()
                break

        # 模式定义
        f_pattern = re.compile(r'^F(\S+)\s+\S+', re.IGNORECASE)
        copy_pattern = re.compile(r'^/\s*COPY\s+(\S+)', re.IGNORECASE)
        include_pattern = re.compile(r'^/\s*INCLUDE\s+(\S+)', re.IGNORECASE)

        # 字段赋值模式
        # EVAL(H) FIELD = value
        eval_pattern = re.compile(r'\bEVAL[HB]?\s+(\S+)\s*=\s*(.+)', re.IGNORECASE)
        # EVALR FIELD = value (带括号)
        evalr_pattern = re.compile(r'\bEVAL[HB]?\s+(\S+)\s*\(\s*=\s*(.+)', re.IGNORECASE)
        # CHAIN/READ 后跟 EVAL
        chain_eval_pattern = re.compile(r'\b(CHAIN|READ|READE|READP|READPE)\s+.*?EVAL\s+(\S+)\s*=\s*(.+)', re.IGNORECASE | re.DOTALL)
        # SETLL/SETGT 后跟 EVAL
        set_pattern = re.compile(r'\b(SETLL|SETGT|SETEQ|SETNE)\s+.*?EVAL\s+(\S+)\s*=\s*(.+)', re.IGNORECASE | re.DOTALL)

        # 文件操作检测
        file_ops = ['CHAIN', 'READ', 'READE', 'READP', 'READPE', 'READC',
                   'WRITE', 'UPDATE', 'DELETE', 'EXFMT', 'EXSR', 'EX CPT',
                   'SETLL', 'SETGT', 'SETEQ', 'SETNE']

        # CALL 模式
        call_pattern = re.compile(r'\bCALL\s+[\'"]?(\S+)[\'"]?', re.IGNORECASE)

        current_file_context = ""

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            upper_stripped = stripped.upper()

            # F 规范
            f_match = f_pattern.match(stripped)
            if f_match:
                file_name = f_match.group(1).upper()
                file_name = re.split(r'[\s(]', file_name)[0]
                current_file_context = file_name

                if file_name and file_name not in info.input_files and file_name not in info.output_files:
                    if any(op in upper_stripped for op in ['DISK', 'WORKSTN', 'K']):
                        info.input_files.append(file_name)
                    elif 'PRINTER' in upper_stripped:
                        info.output_files.append(file_name)
                    else:
                        info.input_files.append(file_name)

                info.file_refs.append(FileReference(
                    file_name=file_name,
                    program_name=program_name,
                    line_number=i,
                    operation='F-Spec'
                ))
                continue

            # /COPY
            copy_match = copy_pattern.match(stripped)
            if copy_match:
                copy_file = copy_match.group(1).upper()
                copy_file = copy_file.split(',')[-1].strip() if ',' in copy_file else copy_file
                info.file_refs.append(FileReference(
                    file_name=copy_file,
                    program_name=program_name,
                    line_number=i,
                    operation='COPY'
                ))
                continue

            # /INCLUDE
            include_match = include_pattern.match(stripped)
            if include_match:
                inc_file = include_match.group(1).upper()
                inc_file = inc_file.split(',')[-1].strip() if ',' in inc_file else inc_file
                info.file_refs.append(FileReference(
                    file_name=inc_file,
                    program_name=program_name,
                    line_number=i,
                    operation='INCLUDE'
                ))
                continue

            # 字段赋值检测 - EVAL
            eval_match = eval_pattern.search(stripped)
            if eval_match:
                field_name = eval_match.group(1).upper()
                value_src = eval_match.group(2).strip()
                # 清理常见后缀
                value_src = re.sub(r'\s+;.*$', '', value_src)

                # 判断值类型
                if value_src.startswith("'") or value_src.startswith('"'):
                    src_type = 'CONSTANT'
                elif re.match(r'^[\d\.]+$', value_src):
                    src_type = 'CONSTANT'
                elif '*' in value_src[:3]:
                    src_type = 'SPECIAL'
                else:
                    src_type = 'EXPRESSION'

                info.field_writes.append(FieldWrite(
                    field_name=field_name,
                    file_name=current_file_context,
                    program_name=program_name,
                    line_number=i,
                    value_source=value_src,
                    operation='EVAL',
                    raw_code=stripped[:100]
                ))
                continue

            # CHAIN 后跟 EVAL (同一行或下一行)
            # 简化处理：检测 CHAIN 操作后记录
            if 'CHAIN' in upper_stripped and 'EVAL' in upper_stripped:
                # 尝试提取 EVAL 部分
                eval_in_chain = re.search(r'EVAL\s+(\S+)\s*=\s*(.+)', upper_stripped, re.IGNORECASE)
                if eval_in_chain:
                    info.field_writes.append(FieldWrite(
                        field_name=eval_in_chain.group(1).upper(),
                        file_name=current_file_context,
                        program_name=program_name,
                        line_number=i,
                        value_source=eval_in_chain.group(2).strip(),
                        operation='CHAIN+EVAL',
                        raw_code=stripped[:100]
                    ))

            # 文件操作记录
            for op in file_ops:
                if re.search(r'\b' + op + r'\b', upper_stripped):
                    # 提取可能的文件名/记录名
                    op_match = re.search(r'\b' + op + r'\s+(\S+)', upper_stripped)
                    if op_match:
                        info.field_refs.append(FieldReference(
                            field_name=op_match.group(1).upper(),
                            file_name=current_file_context,
                            program_name=program_name,
                            line_number=i,
                            operation=op,
                            context='FILE_OP'
                        ))
                    break

            # CALL 指令
            call_match = call_pattern.search(stripped)
            if call_match:
                called = call_match.group(1).strip('\'"').upper()
                if called and not called.startswith('*') and not called.startswith('+'):
                    info.called_programs.append(called)
                    info.call_refs.append(CallReference(
                        called_program=called,
                        calling_program=program_name,
                        line_number=i,
                        call_type='CALL'
                    ))

        info.lines = len(lines)
        return info

    def _parse_rpg(self, content: str, program_name: str, file_path: str) -> ProgramInfo:
        """解析固定格式 RPG"""
        info = ProgramInfo(name=program_name, source_type=SourceType.RPG, path=file_path)
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            if len(line) < 6:
                continue

            col6 = line[5:6].upper()

            # F 规范
            if col6 == 'F':
                file_name = line[6:16].strip().upper()
                if file_name:
                    info.input_files.append(file_name)
                    info.file_refs.append(FileReference(
                        file_name=file_name,
                        program_name=program_name,
                        line_number=i,
                        operation='F-Spec'
                    ))

            # C 规范 - 计算
            elif col6 == 'C':
                # 字段赋值
                calc_line = line[7:65].strip().upper()
                if '=' in calc_line and not calc_line.startswith('*'):
                    parts = calc_line.split('=', 1)
                    if len(parts) == 2:
                        field_name = parts[0].strip().split()[-1] if parts[0].strip().split() else ''
                        if field_name and not field_name.startswith('*'):
                            info.field_writes.append(FieldWrite(
                                field_name=field_name.upper(),
                                program_name=program_name,
                                line_number=i,
                                value_source=parts[1].strip()[:50],
                                operation='C-Spec',
                                raw_code=line.strip()[:100]
                            ))

            # K 规范 - 键字段
            elif col6 == 'K':
                key_fields_line = line[7:].strip()
                kfld_pattern = re.compile(r'KFLD\s+(\S+)', re.IGNORECASE)
                for match in kfld_pattern.finditer(key_fields_line):
                    field_name = match.group(1).upper()
                    info.field_refs.append(FieldReference(
                        field_name=field_name,
                        file_name=program_name,
                        program_name=program_name,
                        line_number=i,
                        operation='K-Spec',
                        context='K',
                        is_key=True
                    ))

            # CALL 在 C 规范
            if col6 == 'C' and 'CALL' in line[7:30].upper():
                call_match = re.search(r'CALL\s+(\S+)', line[7:50].upper())
                if call_match:
                    called = call_match.group(1).strip('\'"').upper()
                    if called and not called.startswith('*'):
                        info.called_programs.append(called)
                        info.call_refs.append(CallReference(
                            called_program=called,
                            calling_program=program_name,
                            line_number=i,
                            call_type='CALL'
                        ))

        info.lines = len(lines)
        return info

    def _parse_cl(self, content: str, program_name: str, file_path: str) -> ProgramInfo:
        """解析 CL 程序"""
        info = ProgramInfo(name=program_name, source_type=SourceType.CL, path=file_path)
        lines = content.split('\n')

        # CALL 模式
        call_pattern = re.compile(r'\bCALL\s+(\S+)', re.IGNORECASE)
        callb_pattern = re.compile(r'\bCALLB\s+.*?(?:PGM|MBR)\s*\(\s*(\S+)', re.IGNORECASE)
        # SBMJOB - 支持多种格式
        sbmjob_pattern = re.compile(r'\bSBMJOB\s+.*?(?:CMD\s*\(\s*)?CALL\s+(?:PGM\s*\(\s*)?(\S+)', re.IGNORECASE)
        sbmjob_cmd_pattern = re.compile(r'\bSBMJOB\s+.*?CMD\s*\(\s*(\S+)', re.IGNORECASE)
        crtpgm_pattern = re.compile(r'\bCRTPGM\s+.*?PGM\s*\(\s*(\S+)', re.IGNORECASE)
        # OVRDBF
        ovrdbf_pattern = re.compile(r'\bOVRDBF\s+FILE\s*\(\s*(\S+)', re.IGNORECASE)
        # CHGVAR 变量赋值
        chgvar_pattern = re.compile(r'\bCHGVAR\s+VAR\s*\(\s*(\&\S+)\s*\)\s+VALUE\s*\(\s*(.+)', re.IGNORECASE)
        # 数据 area
        rtva_pattern = re.compile(r'\bRTVDTAARA\s+DTAARA\s*\(\s*(\S+)', re.IGNORECASE)
        chgdta_pattern = re.compile(r'\bCHGDTAARA\s+DTAARA\s*\(\s*(\S+)', re.IGNORECASE)
        # 数据队列
        sndtaq_pattern = re.compile(r'\bSNDTAQ\s+QUEUE\s*\(\s*(\S+)', re.IGNORECASE)
        rcvdtaq_pattern = re.compile(r'\bRCVTAQ\s+QUEUE\s*\(\s*(\S+)', re.IGNORECASE)
        # 触发器相关
        addtrg_pattern = re.compile(r'\bADDTRG\s+.*?PGM\s*\(\s*(\S+)', re.IGNORECASE)

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            upper_stripped = stripped.upper()

            # CALL
            call_match = call_pattern.search(upper_stripped)
            if call_match:
                called = call_match.group(1).strip('\'"(){}').upper()
                called = re.split(r'[\s)]', called)[0]
                if called and not called.startswith('*'):
                    info.called_programs.append(called)
                    info.call_refs.append(CallReference(
                        called_program=called,
                        calling_program=program_name,
                        line_number=i,
                        call_type='CALL'
                    ))

            # CALLB
            callb_match = callb_pattern.search(upper_stripped)
            if callb_match:
                called = callb_match.group(1).strip('\'"(){}').upper()
                called = re.split(r'[\s)]', called)[0]
                if called and not called.startswith('*'):
                    info.called_programs.append(called)
                    info.call_refs.append(CallReference(
                        called_program=called,
                        calling_program=program_name,
                        line_number=i,
                        call_type='CALLB'
                    ))

            # SBMJOB
            sbmjob_match = sbmjob_pattern.search(upper_stripped)
            if sbmjob_match:
                called = sbmjob_match.group(1).strip('\'"(){}').upper()
                info.indirect_calls.append(IndirectCall(
                    target=called,
                    call_type='SBMJOB',
                    program_name=program_name,
                    line_number=i,
                    details='SBMJOB CMD(CALL PGM(...))'
                ))

            # CRTPGM
            crt_match = crtpgm_pattern.search(upper_stripped)
            if crt_match:
                called = crt_match.group(1).strip('\'"(){}').upper()
                info.indirect_calls.append(IndirectCall(
                    target=called,
                    call_type='CRTPGM',
                    program_name=program_name,
                    line_number=i,
                    details='CRTPGM creates program object'
                ))

            # OVRDBF
            ovrdbf_match = ovrdbf_pattern.search(upper_stripped)
            if ovrdbf_match:
                file_name = ovrdbf_match.group(1).strip('\'"(){}').upper()
                file_name = re.split(r'[\s)]', file_name)[0]
                info.file_refs.append(FileReference(
                    file_name=file_name,
                    program_name=program_name,
                    line_number=i,
                    operation='OVRDBF'
                ))

            # CHGVAR - 变量赋值
            chgvar_match = chgvar_pattern.search(upper_stripped)
            if chgvar_match:
                var_name = chgvar_match.group(1).upper()
                value_src = chgvar_match.group(2).strip()[:50]
                info.field_writes.append(FieldWrite(
                    field_name=var_name,
                    program_name=program_name,
                    line_number=i,
                    value_source=value_src,
                    operation='CHGVAR',
                    raw_code=stripped[:100]
                ))

            # 数据 area 操作
            rtva_match = rtva_pattern.search(upper_stripped)
            if rtva_match:
                dtaara = rtva_match.group(1).strip('\'"(){}').upper()
                info.indirect_calls.append(IndirectCall(
                    target=dtaara,
                    call_type='DTAARA',
                    program_name=program_name,
                    line_number=i,
                    details='RTVDTAARA - Read Data Area'
                ))

            chgdta_match = chgdta_pattern.search(upper_stripped)
            if chgdta_match:
                dtaara = chgdta_match.group(1).strip('\'"(){}').upper()
                info.indirect_calls.append(IndirectCall(
                    target=dtaara,
                    call_type='DTAARA',
                    program_name=program_name,
                    line_number=i,
                    details='CHGDTAARA - Change Data Area'
                ))

            # 触发器
            addtrg_match = addtrg_pattern.search(upper_stripped)
            if addtrg_match:
                pgm = addtrg_match.group(1).strip('\'"(){}').upper()
                info.indirect_calls.append(IndirectCall(
                    target=pgm,
                    call_type='TRIGGER',
                    program_name=program_name,
                    line_number=i,
                    details='ADDTRG - Trigger Program'
                ))

        info.lines = len(lines)
        return info

    def _parse_dds(self, content: str, program_name: str, file_path: str) -> ProgramInfo:
        """解析 DDS 文件定义"""
        info = ProgramInfo(name=program_name, source_type=SourceType.DDS, path=file_path)
        lines = content.split('\n')

        field_pattern = re.compile(r'^A\s+(\S+)\s+(\S+)', re.IGNORECASE)
        key_pattern = re.compile(r'^A\s+K\s+(\S+)', re.IGNORECASE)
        ref_pattern = re.compile(r'^A\s+REF\s*\(\s*(\S+)', re.IGNORECASE)
        unique_pattern = re.compile(r'^A\s+UNIQUE', re.IGNORECASE)

        current_record = program_name
        is_unique = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # UNIQUE 关键字
            if unique_pattern.match(stripped):
                is_unique = True

            # 记录格式名
            if re.match(r'^A\s+NAME\s*\(', stripped, re.IGNORECASE):
                name_match = re.search(r'NAME\s*\(\s*(\S+)', stripped, re.IGNORECASE)
                if name_match:
                    current_record = name_match.group(1).upper()

            # 键字段
            key_match = key_pattern.match(stripped)
            if key_match:
                field_name = key_match.group(1).upper()
                info.field_refs.append(FieldReference(
                    field_name=field_name,
                    file_name=current_record,
                    program_name=program_name,
                    line_number=i,
                    operation='DDS',
                    context='K',
                    is_key=True
                ))

            # 字段定义
            field_match = field_pattern.match(stripped)
            if field_match:
                field_name = field_match.group(1).upper()
                field_type = field_match.group(2).upper()

                if field_name != 'K':
                    info.field_refs.append(FieldReference(
                        field_name=field_name,
                        file_name=current_record,
                        program_name=program_name,
                        line_number=i,
                        operation='DDS',
                        context=field_type,
                        is_key=False
                    ))

            # REF 引用
            ref_match = ref_pattern.search(stripped)
            if ref_match:
                ref_file = ref_match.group(1).upper()
                info.input_files.append(ref_file)
                info.file_refs.append(FileReference(
                    file_name=ref_file,
                    program_name=program_name,
                    line_number=i,
                    operation='REF'
                ))

        info.lines = len(lines)
        return info

    def _parse_generic(self, content: str, program_name: str, file_path: str, source_type: SourceType) -> ProgramInfo:
        """通用解析器"""
        info = ProgramInfo(name=program_name, source_type=source_type, path=file_path)
        info.lines = len(content.split('\n'))
        return info


class LineageAnalyzer:
    """血缘分析器 - 分析程序间的调用关系"""

    def __init__(self, source_dir: str):
        self.source_dir = source_dir
        self.parser = AS400Parser()
        self.programs: Dict[str, ProgramInfo] = {}
        self.file_usage: Dict[str, Set[str]] = defaultdict(set)  # file -> {programs}
        self.field_usage: Dict[str, Set[str]] = defaultdict(set)  # file.field -> {programs}
        self.call_graph: Dict[str, Set[str]] = defaultdict(set)  # program -> {called_programs}
        self.reverse_call_graph: Dict[str, Set[str]] = defaultdict(set)  # program -> {called_by}
        self.field_writes_index: Dict[str, List[FieldValueSource]] = defaultdict(list)  # file.field -> [sources]
        self.indirect_calls_index: Dict[str, List[IndirectCall]] = defaultdict(list)  # program -> [indirect_calls]

    def scan_directory(self, extensions: List[str] = None) -> int:
        """扫描目录下的所有源文件"""
        if extensions is None:
            extensions = ['.rpgle', '.rpg', '.cl', '.clle', '.dds', '.pf', '.lf']

        count = 0
        for root, dirs, files in os.walk(self.source_dir):
            # 跳过隐藏目录和常见无效目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    file_path = os.path.join(root, file)
                    try:
                        info = self.parser.parse_file(file_path)
                        self.programs[info.name] = info
                        count += 1
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")

        self._build_indexes()
        return count

    def _build_indexes(self):
        """构建所有索引"""
        for prog_name, prog_info in self.programs.items():
            # 文件使用索引
            for file_ref in prog_info.file_refs:
                # 标准化文件名
                normalized_file = self._normalize_name(file_ref.file_name)
                self.file_usage[normalized_file].add(prog_name)

                # 如果是 DDS 文件，记录字段
                if prog_info.source_type in [SourceType.DDS, SourceType.PF, SourceType.LF]:
                    for field_ref in prog_info.field_refs:
                        key = f"{prog_name}.{field_ref.field_name}"
                        self.field_usage[key].add(prog_name)

            # 字段使用索引
            for field_ref in prog_info.field_refs:
                if field_ref.file_name:
                    key = f"{field_ref.file_name}.{field_ref.field_name}"
                else:
                    key = f"{prog_name}.{field_ref.field_name}"
                self.field_usage[key].add(prog_name)

            # 调用图
            for called in prog_info.called_programs:
                normalized_called = self._normalize_name(called)
                self.call_graph[prog_name].add(normalized_called)
                self.reverse_call_graph[normalized_called].add(prog_name)

            # 字段赋值索引
            for fw in prog_info.field_writes:
                if fw.file_name:
                    key = f"{fw.file_name}.{fw.field_name}"
                else:
                    key = f"{fw.field_name}"
                self.field_writes_index[key].append(FieldValueSource(
                    program_name=prog_name,
                    line_number=fw.line_number,
                    operation=fw.operation,
                    value_expression=fw.value_source,
                    source_type=self._classify_value_source(fw.value_source),
                    path=prog_info.path
                ))

            # 间接调用索引
            for ic in prog_info.indirect_calls:
                self.indirect_calls_index[prog_name].append(ic)

    def _normalize_name(self, name: str) -> str:
        """标准化对象名称"""
        if not name:
            return ""
        # 去除引号、星号、库限定符
        name = name.strip('\'"*')
        if '/' in name:
            name = name.split('/')[-1]
        if '(' in name:
            name = name.split('(')[0]
        return name.upper()

    def _classify_value_source(self, value: str) -> str:
        """分类赋值来源类型"""
        if not value:
            return 'UNKNOWN'
        value = value.strip()
        if value.startswith("'") or value.startswith('"'):
            return 'CONSTANT'
        if re.match(r'^[\d\.]+$', value):
            return 'CONSTANT'
        if value.startswith('*'):
            return 'SPECIAL'
        if re.match(r'^[\w]+$', value) and len(value) <= 10:
            return 'FIELD'
        return 'EXPRESSION'

    def find_file_usage(self, file_name: str) -> List[str]:
        """查找使用指定文件的所有程序"""
        normalized = self._normalize_name(file_name)
        # 尝试多种匹配
        results = set()

        # 精确匹配
        if normalized in self.file_usage:
            results.update(self.file_usage[normalized])

        # 通配搜索
        for key, progs in self.file_usage.items():
            if normalized in key or key in normalized:
                results.update(progs)

        return sorted(list(results))

    def find_field_usage(self, file_name: str, field_name: str) -> List[str]:
        """查找使用指定字段的所有程序"""
        results = set()

        # 尝试多种 key 格式
        keys_to_try = [
            f"{file_name.upper()}.{field_name.upper()}",
            f"{self._normalize_name(file_name)}.{field_name.upper()}",
        ]

        for key in keys_to_try:
            if key in self.field_usage:
                results.update(self.field_usage[key])
            # 通配匹配
            for k, progs in self.field_usage.items():
                if field_name.upper() in k.split('.')[-1]:
                    results.update(progs)

        return sorted(list(results))

    def get_call_chain(self, program_name: str, depth: int = 10) -> Dict:
        """获取程序调用链"""
        normalized = self._normalize_name(program_name)

        def trace_up(prog: str, visited: Set[str], level: int) -> List:
            if level >= depth or prog in visited or not prog:
                return []
            visited.add(prog)
            result = []
            for caller in self.reverse_call_graph.get(prog, set()):
                if caller and caller not in visited:
                    result.append({
                        'program': caller,
                        'level': level,
                        'children': trace_up(caller, visited.copy(), level + 1)
                    })
            return result

        def trace_down(prog: str, visited: Set[str], level: int) -> List:
            if level >= depth or prog in visited or not prog:
                return []
            visited.add(prog)
            result = []
            for called in self.call_graph.get(prog, set()):
                if called and called not in visited:
                    result.append({
                        'program': called,
                        'level': level,
                        'children': trace_down(called, visited.copy(), level + 1)
                    })
            return result

        return {
            'upstream': trace_up(normalized, set(), 0),
            'downstream': trace_down(normalized, set(), 0)
        }

    def find_field_values_source(self, file_name: str, field_name: str) -> List[FieldValueSource]:
        """查找字段所有可能的赋值来源"""
        results = []

        # 尝试多种 key
        keys_to_try = [
            f"{file_name.upper()}.{field_name.upper()}",
            f"{self._normalize_name(file_name)}.{field_name.upper()}",
            field_name.upper(),
        ]

        for key in keys_to_try:
            if key in self.field_writes_index:
                results.extend(self.field_writes_index[key])

        # 去重
        seen = set()
        unique_results = []
        for r in results:
            identifier = (r.program_name, r.line_number, r.operation)
            if identifier not in seen:
                seen.add(identifier)
                unique_results.append(r)

        return unique_results

    def analyze_indirect_calls(self, program_name: str) -> Dict:
        """分析隐式/间接调用链"""
        normalized = self._normalize_name(program_name)
        result = {
            'sbmjob_calls': [],
            'bnddir_bindings': [],
            'data_area_refs': [],
            'trigger_programs': [],
            'dtaq_refs': [],
            'called_by_indirect': []  # 谁通过间接方式调用了我
        }

        # 收集该程序的间接调用
        if normalized in self.indirect_calls_index:
            for ic in self.indirect_calls_index[normalized]:
                if ic.call_type == 'SBMJOB':
                    result['sbmjob_calls'].append(ic)
                elif ic.call_type == 'DTAARA':
                    result['data_area_refs'].append(ic)
                elif ic.call_type == 'TRIGGER':
                    result['trigger_programs'].append(ic)

        # 查找谁通过间接方式调用了该程序
        for prog, calls in self.indirect_calls_index.items():
            for ic in calls:
                if self._normalize_name(ic.target) == normalized:
                    if ic.call_type == 'SBMJOB':
                        result['called_by_indirect'].append({
                            'caller': prog,
                            'type': 'SBMJOB',
                            'line': ic.line_number
                        })

        return result

    def get_full_lineage_report(self, program_name: str) -> LineageReport:
        """获取完整的血缘分析报告"""
        normalized = self._normalize_name(program_name)
        prog_info = self.programs.get(normalized)

        # 获取基本信息
        file_usage = list(self.find_file_usage(normalized))

        # 获取上下游调用链
        chain = self.get_call_chain(normalized)

        # 获取字段使用情况
        field_usage = {}
        if prog_info:
            for fr in prog_info.field_refs:
                key = f"{fr.file_name}.{fr.field_name}" if fr.file_name else fr.field_name
                progs = self.find_field_usage(fr.file_name or normalized, fr.field_name)
                if progs:
                    field_usage[key] = progs

        # 获取字段赋值来源
        field_writes = []
        if prog_info:
            for fw in prog_info.field_writes:
                if fw.file_name:
                    key = f"{fw.file_name}.{fw.field_name}"
                else:
                    key = fw.field_name
                sources = self.find_field_values_source(fw.file_name or '', fw.field_name)
                field_writes.extend(sources)

        # 获取间接调用
        indirect = self.analyze_indirect_calls(normalized)

        return LineageReport(
            program_name=normalized,
            file_usage=file_usage,
            field_usage=field_usage,
            upstream=chain['upstream'],
            downstream=chain['downstream'],
            field_writes=field_writes,
            indirect_calls=[
                IndirectCall(
                    target=t,
                    call_type=ct,
                    program_name=p,
                    line_number=l,
                    details=d
                )
                for p, calls in self.indirect_calls_index.items()
                for ic in calls
                if p == normalized
                for t, ct, l, d in [(ic.target, ic.call_type, ic.line_number, ic.details)]
            ]
        )

    def search_programs(self, keyword: str) -> List[str]:
        """搜索程序名包含关键字的程序"""
        keyword = keyword.upper()
        return [p for p in self.programs.keys() if keyword in p]

    def get_program_info(self, program_name: str) -> Optional[ProgramInfo]:
        """获取程序详细信息"""
        normalized = self._normalize_name(program_name)
        return self.programs.get(normalized)


# 格式化输出函数
def format_call_tree(trees: List[Dict], prefix: str = "", is_last: bool = True) -> str:
    """格式化调用树"""
    lines = []
    for i, node in enumerate(trees):
        is_last_node = (i == len(trees) - 1)
        connector = "└─ " if is_last_node else "├─ "
        lines.append(f"{prefix}{connector}{node['program']}")
        if node.get('children'):
            extension = "    " if is_last_node else "│   "
            lines.append(format_call_tree(node['children'], prefix + extension, is_last_node))
    return '\n'.join(lines)

def format_lineage_report(report: LineageReport) -> str:
    """格式化血缘报告"""
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"📊 血缘分析报告: {report.program_name}")
    lines.append(f"{'='*60}\n")

    # 文件使用
    lines.append(f"📂 使用文件 ({len(report.file_usage)}):")
    if report.file_usage:
        for f in report.file_usage[:20]:
            lines.append(f"   • {f}")
        if len(report.file_usage) > 20:
            lines.append(f"   ... 还有 {len(report.file_usage) - 20} 个")
    else:
        lines.append("   (无)")

    # 调用链
    lines.append(f"\n📤 向上调用 (谁调用了我):")
    if report.upstream:
        lines.append(format_call_tree(report.upstream))
    else:
        lines.append("   (无)")

    lines.append(f"\n📥 向下调用 (我调用了谁):")
    if report.downstream:
        lines.append(format_call_tree(report.downstream))
    else:
        lines.append("   (无)")

    # 字段赋值
    if report.field_writes:
        lines.append(f"\n✏️  字段赋值来源 ({len(report.field_writes)}):")
        for fw in report.field_writes[:15]:
            lines.append(f"   • {fw.program_name}:{fw.line_number} [{fw.operation}] {fw.field_name if hasattr(fw, 'field_name') else '?'} = {fw.value_expression[:30]}")
        if len(report.field_writes) > 15:
            lines.append(f"   ... 还有 {len(report.field_writes) - 15} 个")

    # 间接调用
    if report.indirect_calls:
        lines.append(f"\n🔗 间接调用 ({len(report.indirect_calls)}):")
        for ic in report.indirect_calls:
            lines.append(f"   • [{ic.call_type}] {ic.target} @ line {ic.line_number}")

    lines.append(f"\n{'='*60}")
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("AS400 Program Analyzer v2.0")
        print("Usage: python analyzer.py <source_directory> [command] [args]")
        print("\nCommands:")
        print("  scan                  - 扫描目录")
        print("  file-usage <file>     - 查找文件使用")
        print("  field-usage <file.field> - 查找字段使用")
        print("  call-chain <pgm>      - 追踪调用链")
        print("  field-values <file.field> - 字段赋值来源")
        print("  indirect <pgm>       - 间接调用分析")
        print("  report <pgm>          - 完整血缘报告")
        print("  search <keyword>      - 搜索程序")
        sys.exit(1)

    source_dir = sys.argv[1]
    analyzer = LineageAnalyzer(source_dir)

    if len(sys.argv) == 2:
        count = analyzer.scan_directory()
        print(f"✅ 已扫描 {count} 个程序")
        print(f"   文件索引: {len(analyzer.file_usage)} 个文件")
        print(f"   程序索引: {len(analyzer.programs)} 个程序")
        print(f"   字段写入索引: {len(analyzer.field_writes_index)} 条")

    elif len(sys.argv) >= 3:
        cmd = sys.argv[2]

        if cmd == 'scan':
            count = analyzer.scan_directory()
            print(f"✅ 已扫描 {count} 个程序")

        elif cmd == 'file-usage' and len(sys.argv) >= 4:
            programs = analyzer.find_file_usage(sys.argv[3])
            print(f"📂 文件 '{sys.argv[3]}' 被以下 {len(programs)} 个程序使用:")
            for p in programs:
                print(f"   • {p}")

        elif cmd == 'field-usage' and len(sys.argv) >= 4:
            field_arg = sys.argv[3]
            if '.' in field_arg:
                file_name, field_name = field_arg.split('.', 1)
                programs = analyzer.find_field_usage(file_name, field_name)
                print(f"📋 字段 '{field_arg}' 被以下 {len(programs)} 个程序使用:")
                for p in programs:
                    print(f"   • {p}")
            else:
                print("❌ 请使用 file.field 格式")

        elif cmd == 'call-chain' and len(sys.argv) >= 4:
            chain = analyzer.get_call_chain(sys.argv[3])
            print(f"🔗 '{sys.argv[3]}' 调用链\n")
            print(f"📤 向上调用 (谁调用了我):")
            if chain['upstream']:
                print(format_call_tree(chain['upstream']))
            else:
                print("   (无)")
            print(f"\n📥 向下调用 (我调用了谁):")
            if chain['downstream']:
                print(format_call_tree(chain['downstream']))
            else:
                print("   (无)")

        elif cmd == 'field-values' and len(sys.argv) >= 4:
            field_arg = sys.argv[3]
            if '.' in field_arg:
                file_name, field_name = field_arg.split('.', 1)
                sources = analyzer.find_field_values_source(file_name, field_name)
                print(f"✏️  字段 '{field_arg}' 赋值来源 ({len(sources)}):")
                for s in sources:
                    print(f"   • {s.program_name}:{s.line_number} [{s.operation}] {s.value_expression[:50]}")
            else:
                print("❌ 请使用 file.field 格式")

        elif cmd == 'indirect' and len(sys.argv) >= 4:
            result = analyzer.analyze_indirect_calls(sys.argv[3])
            print(f"🔗 '{sys.argv[3]}' 间接调用分析\n")
            if result['sbmjob_calls']:
                print(f"📤 SBMJOB 调用 ({len(result['sbmjob_calls'])}):")
                for ic in result['sbmjob_calls']:
                    print(f"   • {ic.target} @ line {ic.line_number}")
            if result['data_area_refs']:
                print(f"\n📦 Data Area 引用 ({len(result['data_area_refs'])}):")
                for ic in result['data_area_refs']:
                    print(f"   • {ic.target} [{ic.details}]")
            if result['trigger_programs']:
                print(f"\n⚡ Trigger 程序 ({len(result['trigger_programs'])}):")
                for ic in result['trigger_programs']:
                    print(f"   • {ic.target}")
            if result['called_by_indirect']:
                print(f"\n👥 通过间接方式调用我的程序 ({len(result['called_by_indirect'])}):")
                for ic in result['called_by_indirect']:
                    print(f"   • {ic['caller']} [{ic['type']}]")
            if not any(result.values()):
                print("   (无间接调用)")

        elif cmd == 'report' and len(sys.argv) >= 4:
            report = analyzer.get_full_lineage_report(sys.argv[3])
            print(format_lineage_report(report))

        elif cmd == 'search' and len(sys.argv) >= 4:
            results = analyzer.search_programs(sys.argv[3])
            print(f"🔍 搜索 '{sys.argv[3]}' 结果 ({len(results)}):")
            for p in results[:50]:
                print(f"   • {p}")
            if len(results) > 50:
                print(f"   ... 还有 {len(results) - 50} 个")

        else:
            print(f"❌ 未知命令: {cmd}")
            print("使用 'python analyzer.py <dir>' 查看帮助")
