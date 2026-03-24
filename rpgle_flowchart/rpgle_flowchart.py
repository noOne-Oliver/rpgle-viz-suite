#!/usr/bin/env python3
"""
RPGLE Flowchart Generator v2.0
Generate Mermaid/PlantUML flowcharts from RPGLE, SQLRPGLE, and CLLE source.
Enhanced with: SQLRPGLE support, API mode, batch processing, statistics, PlantUML output.
"""
import argparse, re, sys, pathlib, json, subprocess
from dataclasses import dataclass, field
from typing import Optional

VERSION = "2.0.0"

# ============ Constants ============

COMMENT_RE = re.compile(r'^\s*(//|\*\*|/\*|\*)')
RPG_KW = {
    'if':'IF', 'elseif':'ELSEIF', 'else':'ELSE', 'endif':'ENDIF',
    'select':'SELECT', 'when':'WHEN', 'other':'OTHER', 'endsl':'ENDSL',
    'dow':'DOW', 'dou':'DOU', 'enddo':'ENDDO',
    'for':'FOR', 'endfor':'ENDFOR',
    'monitor':'MONITOR', 'on-error':'ON-ERROR', 'endmon':'ENDMON',
    'leave':'LEAVE', 'iter':'ITER', 'return':'RETURN',
    'callp':'CALLP', 'exsr':'EXSR', 'call':'CALL', 'callb':'CALLB',
    'dcl-proc':'DCL-PROC', 'end-proc':'END-PROC',
    'begsr':'BEGSR', 'endsr':'ENDSR',
    'chain':'CHAIN','read':'READ','reade':'READE','readp':'READP','readpe':'READPE',
    'write':'WRITE','update':'UPDATE','delete':'DELETE',
    # SQL
    'exec':'EXEC', 'sql':'SQL', 'execute':'EXECUTE'
}
CL_KW = {
    'if':'IF', 'then':'THEN', 'else':'ELSE', 'endif':'ENDIF',
    'do':'DO', 'enddo':'ENDDO', 'dowhile':'DOWHILE',
    'dountil':'DOUNTIL', 'select':'SELECT', 'when':'WHEN', 'other':'OTHER', 'endselect':'ENDSELECT',
    'call':'CALL', 'callpgm':'CALLPGM', 'return':'RETURN'
}
FIXED_OPS = {
    'if','andif','orif','else','endif',
    'dow','dou','do','enddo','for','endfor',
    'select','when','other','endsl',
    'begsr','endsr','exsr',
    'call','callb','callp',
    'return','leave','iter',
    'monitor','on-error','endmon',
    'chain','read','reade','readp','readpe','write','update','delete'
}
STYLE_TEMPLATES = {
    'default': '',
    'dark': """%%{init: {'theme':'dark','themeVariables':{'primaryColor':'#1f2937','primaryTextColor':'#f9fafb','lineColor':'#93c5fd','secondaryColor':'#111827','tertiaryColor':'#374151'}}}%%""",
    'pastel': """%%{init: {'theme':'base','themeVariables':{'primaryColor':'#dbeafe','primaryTextColor':'#111827','lineColor':'#60a5fa','secondaryColor':'#fde68a','tertiaryColor':'#fbcfe8'}}}%%"""
}

# ============ Data Classes ============

@dataclass
class Node:
    nid: str
    label: str
    shape: str = 'process'
    group: str = 'MAIN'
    io_type: Optional[str] = None

    def mermaid(self) -> str:
        if self.shape == 'decision': return f'{self.nid}{{{self.label}}}'
        if self.shape == 'terminal': return f'{self.nid}([{self.label}])'
        if self.shape == 'io': return f'{self.nid}[/{self.label}/]'
        return f'{self.nid}[{self.label}]'

    def plantuml(self) -> str:
        if self.shape == 'decision': return f'{"yes"} -> {self.nid}\n{self.nid} is {self.label}'
        if self.shape == 'terminal': return f'({self.label})'
        if self.shape == 'io': return f'[{self.label}]'
        return f'{self.label}'

@dataclass
class Flow:
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    n: int = 0
    stats: dict = field(default_factory=lambda: {
        'if_count': 0, 'select_count': 0, 'loop_count': 0,
        'io_count': 0, 'call_count': 0, 'monitor_count': 0,
        'sql_count': 0
    })

    def add_node(self, label: str, shape: str = 'process', group: str = 'MAIN') -> str:
        self.n += 1
        node = Node(f'N{self.n}', label, shape, group)
        self.nodes.append(node)
        return node.nid

    def add_edge(self, src: str, dst: str, label: Optional[str] = None):
        self.edges.append((src, dst, label))

    def to_mermaid(self, style: str = 'default') -> str:
        lines = []
        if style in STYLE_TEMPLATES and STYLE_TEMPLATES[style]:
            lines.append(STYLE_TEMPLATES[style])
        lines.append('flowchart TD')
        groups = {}
        for n in self.nodes:
            groups.setdefault(n.group, []).append(n)
        for g, nodes in groups.items():
            gid = re.sub(r'[^A-Za-z0-9_]', '_', g)
            lines.append(f'    subgraph {gid}["{g}"]')
            for n in nodes:
                lines.append(f'        {n.mermaid()}')
            lines.append('    end')
        for src, dst, label in self.edges:
            if label:
                lines.append(f'    {src} -- "{label}" --> {dst}')
            else:
                lines.append(f'    {src} --> {dst}')
        return '\n'.join(lines) + '\n'

    def to_plantuml(self) -> str:
        lines = ['@startuml']
        groups = {}
        for n in self.nodes:
            groups.setdefault(n.group, []).append(n)
        for g, nodes in groups.items():
            lines.append(f'partition {g} {{')
            for n in nodes:
                if n.shape == 'decision':
                    lines.append(f'if ({n.label}) then')
                elif n.shape == 'terminal':
                    lines.append(f':{n.label};')
                elif n.shape == 'io':
                    lines.append(f':{n.label};')
                else:
                    lines.append(f':{n.label};')
            lines.append('}')
        for src, dst, label in self.edges:
            if label:
                lines.append(f'{src} --> {dst} : {label}')
            else:
                lines.append(f'{src} --> {dst}')
        lines.append('@enduml')
        return '\n'.join(lines) + '\n'

    def to_json(self) -> str:
        return json.dumps({
            'nodes': [{'id': n.nid, 'label': n.label, 'shape': n.shape, 'group': n.group} for n in self.nodes],
            'edges': [{'from': e[0], 'to': e[1], 'label': e[2]} for e in self.edges],
            'stats': self.stats
        }, indent=2)

    def complexity_score(self) -> int:
        return (self.stats['if_count'] * 2 +
                self.stats['select_count'] * 3 +
                self.stats['loop_count'] * 2 +
                self.stats['monitor_count'] * 2 +
                self.stats['io_count'] +
                self.stats['call_count'])

    def complexity_label(self) -> str:
        score = self.complexity_score()
        if score < 20: return 'Low'
        if score < 50: return 'Medium'
        if score < 100: return 'High'
        return 'Very High'

# ============ Parsers ============

def normalize_line(line: str) -> str:
    if '//' in line: line = line.split('//', 1)[0]
    return line.strip()

def detect_fixed_comment(line: str) -> bool:
    return len(line) >= 7 and line[6] == '*'

def guess_lang(path: pathlib.Path, text_lines: list) -> str:
    ext = path.suffix.lower()
    if ext in ('.clle', '.clp', '.cl'): return 'clle'
    for l in text_lines[:50]:
        if l.strip().lower().startswith('**free') or l.strip().lower().startswith('**sql'): return 'rpgle'
    return 'rpgle'

def safe_group_id(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]', '_', name)

def _clean_name(name: str) -> str:
    return re.sub(r'[;()]+', '', name or '')

def extract_call_target(line: str):
    for pattern in [r'\bcallp?\b\s+([A-Za-z0-9_@$#]+)', r'\bexsr\b\s+([A-Za-z0-9_@$#]+)', r'\bcallb\b\s+([A-Za-z0-9_@$#]+)']:
        m = re.search(pattern, line, re.IGNORECASE)
        if m: return _clean_name(m.group(1))
    return None

def fixed_opcode_and_operand(line: str):
    opcode = line[25:35].strip().lower() if len(line) >= 35 else ''
    if not opcode: return None, None
    factor1 = line[6:20].strip() if len(line) >= 20 else ''
    tail = line[35:].strip() if len(line) > 35 else ''
    operand = factor1 or (tail.split()[0] if tail else '')
    return opcode, operand

class BaseParser:
    def __init__(self, lines: list):
        self.lines = lines
        self.flow = Flow()
        self.stack = []
        self.group_stack = []
        self.current_group = 'MAIN'
        self.current_by_group = {}
        self.module_entries = {}
        self.pending_links = []
        self.in_sql_block = False
        self.sql_buffer = []

        start = self.flow.add_node('Start', 'terminal', self.current_group)
        self.current = start
        self.current_by_group[self.current_group] = start
        self.module_entries['MAIN'] = start

    def _set_group(self, group_name: str):
        self.current_group = group_name
        if group_name not in self.current_by_group:
            entry = self.flow.add_node(f'{group_name} ENTRY', 'terminal', group_name)
            self.current_by_group[group_name] = entry
            self.module_entries[group_name] = entry
        self.current = self.current_by_group[group_name]

    def _push_group(self, group_name: str):
        self.group_stack.append(self.current_group)
        self._set_group(group_name)

    def _pop_group(self):
        if self.group_stack: self._set_group(self.group_stack.pop())

    def _add_step(self, text: str, link_target: Optional[str] = None, io_type: Optional[str] = None):
        nid = self.flow.add_node(text, 'io' if io_type else 'process', self.current_group)
        if io_type: self.flow.nodes[-1].io_type = io_type
        self.flow.add_edge(self.current, nid)
        self.current = nid
        self.current_by_group[self.current_group] = nid
        if link_target: self.pending_links.append((nid, link_target))

    def _finish(self):
        for group, cur in list(self.current_by_group.items()):
            end = self.flow.add_node('End', 'terminal', group)
            self.flow.add_edge(cur, end)
        for src, tgt in self.pending_links:
            key = None
            if tgt is None: continue
            for prefix in ['PROC:', 'SR:']:
                if f'{prefix}{tgt.upper()}' in self.module_entries:
                    key = f'{prefix}{tgt.upper()}'
                    break
            if not key and tgt.upper() in self.module_entries: key = tgt.upper()
            if key: self.flow.add_edge(src, self.module_entries[key], 'calls')
        return self.flow

    def handle_sql(self, sql_text: str):
        self.flow.stats['sql_count'] += 1
        sql_clean = ' '.join(sql_text.split())[:50]
        self._add_step(f'SQL: {sql_clean}...', io_type='sql')

    def handle_if(self, label: str):
        nid = self.flow.add_node(f'IF {label}', 'decision', self.current_group)
        self.flow.add_edge(self.current, nid)
        self.stack.append({'type':'IF', 'id':nid, 'else':None, 'group':self.current_group})
        self.current = nid
        self.flow.stats['if_count'] += 1

    def handle_else(self):
        if not self.stack or self.stack[-1]['type'] != 'IF': self._add_step('ELSE'); return
        ctx = self.stack[-1]
        self.current = self.flow.add_node('ELSE', 'process', self.current_group)
        self.flow.add_edge(ctx['id'], self.current, 'No')
        ctx['else'] = self.current

    def handle_endif(self):
        if not self.stack or self.stack[-1]['type'] != 'IF': self._add_step('ENDIF'); return
        ctx = self.stack.pop()
        join = self.flow.add_node('END IF', group=self.current_group)
        self.flow.add_edge(self.current, join)
        if ctx.get('else') is None: self.flow.add_edge(ctx['id'], join, 'No')
        self.current = join
        self.current_by_group[self.current_group] = join

    def handle_loop_start(self, label: str):
        dec = self.flow.add_node(label, 'decision', self.current_group)
        self.flow.add_edge(self.current, dec)
        self.stack.append({'type':'LOOP', 'id':dec, 'group':self.current_group})
        self.current = dec
        self.flow.stats['loop_count'] += 1

    def handle_loop_end(self, end_label: str = 'END DO'):
        if not self.stack or self.stack[-1]['type'] != 'LOOP': self._add_step(end_label); return
        ctx = self.stack.pop()
        self.flow.add_edge(self.current, ctx['id'], 'Loop')
        exit_node = self.flow.add_node(end_label, group=self.current_group)
        self.flow.add_edge(ctx['id'], exit_node, 'Exit')
        self.current = exit_node
        self.current_by_group[self.current_group] = exit_node

    def handle_select(self):
        dec = self.flow.add_node('SELECT', 'decision', self.current_group)
        self.flow.add_edge(self.current, dec)
        self.stack.append({'type':'SELECT', 'id':dec, 'group':self.current_group})
        self.current = dec
        self.flow.stats['select_count'] += 1

    def handle_when(self, label: str):
        if not self.stack or self.stack[-1]['type'] != 'SELECT': self._add_step(f'WHEN {label}'); return
        ctx = self.stack[-1]
        node = self.flow.add_node(f'WHEN {label}', 'process', self.current_group)
        self.flow.add_edge(ctx['id'], node, 'Yes')
        self.current = node

    def handle_other(self):
        if not self.stack or self.stack[-1]['type'] != 'SELECT': self._add_step('OTHER'); return
        ctx = self.stack[-1]
        node = self.flow.add_node('OTHER', 'process', self.current_group)
        self.flow.add_edge(ctx['id'], node, 'No')
        self.current = node

    def handle_endselect(self, label: str = 'END SELECT'):
        if not self.stack or self.stack[-1]['type'] != 'SELECT': self._add_step(label); return
        self.stack.pop()
        join = self.flow.add_node(label, group=self.current_group)
        self.flow.add_edge(self.current, join)
        self.current = join
        self.current_by_group[self.current_group] = join

    def handle_monitor(self):
        self._add_step('MONITOR')
        self.flow.stats['monitor_count'] += 1

    def handle_on_error(self, label: str):
        self._add_step(f'ON-ERROR {label}')

    def handle_return(self):
        node = self.flow.add_node('RETURN', 'terminal', self.current_group)
        self.flow.add_edge(self.current, node)
        self.current = node
        self.current_by_group[self.current_group] = node

    def handle_io(self, kw: str, line: str, token: str):
        label = f'{kw} {line[len(token):].strip()}'.strip()
        nid = self.flow.add_node(label, 'io', self.current_group)
        self.flow.nodes[-1].io_type = kw.lower()
        self.flow.add_edge(self.current, nid)
        self.current = nid
        self.current_by_group[self.current_group] = nid
        self.flow.stats['io_count'] += 1

    def handle_call(self, kw: str, line: str):
        tgt = extract_call_target(line)
        self._add_step(line, tgt)
        self.flow.stats['call_count'] += 1

class RPGParser(BaseParser):
    def handle_line(self, line: str, raw: str):
        lower = line.lower()
        token = lower.split()[0]

        # SQL block detection
        if 'exec sql' in lower or 'execute sql' in lower:
            self.in_sql_block = True
            self.sql_buffer = []
        if self.in_sql_block:
            self.sql_buffer.append(line)
            if ';' in line and not self.sql_buffer[0].startswith('EXEC SQL'):
                self.handle_sql(' '.join(self.sql_buffer))
                self.in_sql_block = False
                self.sql_buffer = []
            return

        if token in RPG_KW:
            kw = RPG_KW[token]
            if kw == 'IF': self.handle_if(line[len('if'):].strip()); return
            if kw == 'ELSEIF': self.handle_else(); self.handle_if(line[len('elseif'):].strip()); return
            if kw == 'ELSE': self.handle_else(); return
            if kw == 'ENDIF': self.handle_endif(); return
            if kw in ('DOW','DOU'): self.handle_loop_start(f'{kw} {line[len(token):].strip()}'); return
            if kw == 'ENDDO': self.handle_loop_end('END DO'); return
            if kw == 'FOR': self.handle_loop_start(f'FOR {line[len("for"):].strip()}'); return
            if kw == 'ENDFOR': self.handle_loop_end('END FOR'); return
            if kw == 'SELECT': self.handle_select(); return
            if kw == 'WHEN': self.handle_when(line[len('when'):].strip()); return
            if kw == 'OTHER': self.handle_other(); return
            if kw == 'ENDSL': self.handle_endselect('END SELECT'); return
            if kw == 'MONITOR': self.handle_monitor(); return
            if kw == 'ON-ERROR': self.handle_on_error(line[len('on-error'):].strip()); return
            if kw == 'ENDMON': self._add_step('END MONITOR'); return
            if kw == 'RETURN': self.handle_return(); return
            if kw in ('CALL','CALLP','CALLB','EXSR'): self.handle_call(kw, line); return
            if kw in ('CHAIN','READ','READE','READP','READPE','WRITE','UPDATE','DELETE'): self.handle_io(kw, line, token); return

        opcode, operand = fixed_opcode_and_operand(raw)
        if opcode and opcode in FIXED_OPS:
            if opcode in ('if','andif','orif'): self.handle_if(raw[35:].strip() or line); return
            if opcode == 'else': self.handle_else(); return
            if opcode == 'endif': self.handle_endif(); return
            if opcode in ('dow','dou','do','for'): self.handle_loop_start(f'{opcode.upper()} {raw[35:].strip()}'); return
            if opcode in ('enddo','endfor'): self.handle_loop_end('END DO'); return
            if opcode == 'select': self.handle_select(); return
            if opcode == 'when': self.handle_when(raw[35:].strip()); return
            if opcode == 'other': self.handle_other(); return
            if opcode == 'endsl': self.handle_endselect('END SELECT'); return
            if opcode == 'begsr':
                name = _clean_name((operand or 'SR')).upper()
                self._push_group(f'SR:{name}'); return
            if opcode == 'endsr': self._pop_group(); return
            if opcode in ('call','callb','callp','exsr'):
                self.handle_call(opcode.upper(), raw.strip()); return
            if opcode in ('chain','read','reade','readp','readpe','write','update','delete'):
                self.handle_io(opcode.upper(), opcode.upper() + ' ' + (operand or ''), opcode); return
            if opcode == 'return': self.handle_return(); return
            if opcode == 'monitor': self.handle_monitor(); return
            if opcode == 'on-error': self.handle_on_error(operand or ''); return
        self._add_step(line)

class CLParser(BaseParser):
    def handle_line(self, line: str, raw: str):
        lower = line.lower()
        token = lower.split()[0]
        if token in CL_KW:
            kw = CL_KW[token]
            if kw == 'IF': self.handle_if(line[len('if'):].strip()); return
            if kw == 'ELSE': self.handle_else(); return
            if kw == 'ENDIF': self.handle_endif(); return
            if kw in ('DO','DOWHILE','DOUNTIL'): self.handle_loop_start(f'{kw} {line[len(token):].strip()}'); return
            if kw == 'ENDDO': self.handle_loop_end('END DO'); return
            if kw == 'SELECT': self.handle_select(); return
            if kw == 'WHEN': self.handle_when(line[len('when'):].strip()); return
            if kw == 'OTHER': self.handle_other(); return
            if kw == 'ENDSELECT': self.handle_endselect('END SELECT'); return
            if kw == 'RETURN': self.handle_return(); return
            if kw in ('CALL','CALLPGM'): self.handle_call(kw, line); return
        self._add_step(line)

def parse_file(path: pathlib.Path, lang: str = 'auto') -> Flow:
    text = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    if lang == 'auto': lang = guess_lang(path, text)
    parser = RPGParser(text) if lang == 'rpgle' else CLParser(text)
    for raw in text:
        line = raw.rstrip('\n')
        if not line.strip(): continue
        if detect_fixed_comment(line): continue
        line = normalize_line(line)
        if not line or COMMENT_RE.match(line): continue
        parser.handle_line(line, raw)
    return parser._finish()

def to_html(mmd: str, title: str = 'Mermaid Diagram') -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ margin: 0; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial; }}
    .mermaid {{ width: 100%; }}
  </style>
</head>
<body>
  <div class="mermaid">\n{mmd}\n</div>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true }});
  </script>
</body>
</html>
"""

def print_stats(flow: Flow, path: pathlib.Path):
    stats = flow.stats
    score = flow.complexity_score()
    label = flow.complexity_label()
    print(f"📊 Flowchart Statistics: {path.name}")
    print(f"\nControl Structures:")
    print(f"├─ IF/ELSE: {stats['if_count']}")
    print(f"├─ SELECT/WHEN: {stats['select_count']}")
    print(f"├─ Loops (DOW/DOU/FOR): {stats['loop_count']}")
    print(f"├─ MONITOR/ON-ERROR: {stats['monitor_count']}")
    print(f"└─ SQL Blocks: {stats['sql_count']}")
    print(f"\nOperations:")
    print(f"├─ I/O (CHAIN/READ/WRITE...): {stats['io_count']}")
    print(f"└─ Calls (CALL/CALLB/SBMJOB): {stats['call_count']}")
    print(f"\nComplexity Score: {score} ({label})")

def validate() -> bool:
    print(f"✅ RPGLE Flowchart v{VERSION} - Self Validation")
    print(f"   Testing free-format IF/ELSE...")
    test_code = [
        "**FREE",
        "IF condition = 'Y';",
        "  EXSR mySub;",
        "ELSE;",
        "  RETURN;",
        "ENDIF;"
    ]
    parser = RPGParser(test_code)
    for raw in test_code:
        line = raw.rstrip('\n')
        if not line.strip(): continue
        line = normalize_line(line)
        if not line or COMMENT_RE.match(line): continue
        parser.handle_line(line, raw)
    flow = parser._finish()
    assert flow.stats['if_count'] == 1, f"IF count mismatch: {flow.stats['if_count']}"
    print(f"   ✅ Free-format IF/ELSE parsed correctly")
    print(f"\n✅ All validations passed!")
    return True

# ============ CLI ============

def main():
    ap = argparse.ArgumentParser(description=f'RPGLE Flowchart Generator v{VERSION}')
    ap.add_argument('input', nargs='?', help='Input file or directory')
    ap.add_argument('-o', '--output', help='Output file')
    ap.add_argument('--format', choices=['mermaid','plantuml','html','json'], default='mermaid', help='Output format')
    ap.add_argument('--style', choices=['default','dark','pastel'], default='default', help='Mermaid theme')
    ap.add_argument('--lang', choices=['auto','rpgle','clle'], default='auto')
    ap.add_argument('--stats', action='store_true', help='Show statistics')
    ap.add_argument('--batch', action='store_true', help='Batch process directory')
    ap.add_argument('--output-dir', help='Output directory for batch mode')
    ap.add_argument('--validate', action='store_true', help='Run validation tests')
    ap.add_argument('--interactive', action='store_true', help='Interactive mode')
    args = ap.parse_args()

    if args.validate:
        sys.exit(0 if validate() else 1)

    if args.interactive:
        print("Interactive mode - Type 'quit' to exit")
        while True:
            try:
                cmd = input("> ").strip()
                if cmd.lower() in ('quit', 'exit', 'q'): break
                if cmd: print(f"Processing: {cmd}")
            except EOFError: break
        return

    if not args.input:
        ap.print_help()
        return

    input_path = pathlib.Path(args.input)
    if args.batch and input_path.is_dir():
        output_dir = pathlib.Path(args.output_dir) if args.output_dir else input_path
        output_dir.mkdir(parents=True, exist_ok=True)
        for f in input_path.rglob('*.rpg*'):
            try:
                flow = parse_file(f, args.lang)
                ext = '.mmd' if args.format == 'mermaid' else f'.{args.format}'
                out_file = output_dir / f'{f.stem}{ext}'
                if args.format == 'html':
                    out_file.write_text(to_html(flow.to_mermaid(args.style), f.name))
                elif args.format == 'json':
                    out_file.write_text(flow.to_json())
                elif args.format == 'plantuml':
                    out_file.write_text(flow.to_plantuml())
                else:
                    out_file.write_text(flow.to_mermaid(args.style))
                print(f"✅ {f.name} -> {out_file.name}")
            except Exception as e:
                print(f"❌ {f.name}: {e}")
    else:
        if not input_path.exists():
            print(f"Error: {input_path} not found")
            sys.exit(1)
        flow = parse_file(input_path, args.lang)
        if args.stats: print_stats(flow, input_path)
        output = args.output
        if args.format == 'html':
            content = to_html(flow.to_mermaid(args.style), input_path.name)
        elif args.format == 'json':
            content = flow.to_json()
        elif args.format == 'plantuml':
            content = flow.to_plantuml()
        else:
            content = flow.to_mermaid(args.style)
        if output:
            pathlib.Path(output).write_text(content)
            print(f"✅ Written to {output}")
        else:
            sys.stdout.write(content)

if __name__ == '__main__':
    main()
