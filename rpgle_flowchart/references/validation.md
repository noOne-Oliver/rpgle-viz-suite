# Validation Framework

## Running Validation

```bash
python3 scripts/rpgle_flowchart.py --validate
```

## Test Suite

### 1. Basic Control Structures

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| IF/ELSE | `IF x=1; ... ELSE; ... ENDIF` | if_count=1 | ✅ |
| SELECT/WHEN | `SELECT; WHEN x=1; ... ENDSELECT` | select_count=1 | ✅ |
| DOW loop | `DOW x<10; ... ENDDO` | loop_count=1 | ✅ |
| FOR loop | `FOR i=1 to 10; ... ENDFOR` | loop_count=1 | ✅ |
| MONITOR | `MONITOR; ... ON-ERROR; ... ENDMON` | monitor_count=1 | ✅ |

### 2. I/O Operations

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| CHAIN | `CHAIN (k) FILE` | io_count=1, type=chain | ✅ |
| READ | `READ FILE` | io_count=1, type=read | ✅ |
| WRITE | `WRITE RFORMAT` | io_count=1, type=write | ✅ |
| UPDATE | `UPDATE RFORMAT` | io_count=1, type=update | ✅ |
| DELETE | `DELETE RFORMAT` | io_count=1, type=delete | ✅ |

### 3. Program Calls

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| CALL | `CALL 'PGM001'` | call_count=1 | ✅ |
| CALLP | `CALLP PGM002` | call_count=1 | ✅ |
| CALLB | `CALLB SRVPGM` | call_count=1 | ✅ |
| EXSR | `EXSR MYSR` | sr_call=1 | ✅ |

### 4. Fixed Format RPG

| Test | Detection | Expected | Status |
|------|-----------|----------|--------|
| Column 7 asterisk | ` *` at col 7 | lang=rpg | ✅ |
| Fixed IF | C-spec IF at col 26 | if_count=1 | ✅ |
| Fixed DO | C-spec DO at col 26 | loop_count=1 | ✅ |

### 5. SQLRPGLE

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| EXEC SQL block | `EXEC SQL ... ;` | sql_count=1 | ✅ |
| Multiple SQL | 3 SQL blocks | sql_count=3 | ✅ |

### 6. Complexity Score

| Program Type | Expected Range |
|--------------|----------------|
| Simple (1-5 statements) | < 20 (Low) |
| Medium (subroutine) | 20-50 (Medium) |
| Complex (multiple loops/conditions) | 50-100 (High) |
| Very Complex | > 100 (Very High) |

## Self-Check Checklist

Before marking a feature as complete:

- [ ] All test cases pass
- [ ] Edge cases handled (empty input, malformed code)
- [ ] Both Mermaid and PlantUML output valid
- [ ] JSON output parseable
- [ ] Statistics accurate
- [ ] CLI --help accurate
- [ ] No hardcoded paths
