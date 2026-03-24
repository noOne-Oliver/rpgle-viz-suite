# Patterns - Complex Structure Examples

## Nested IF Structures

```rpgle
IF cond1;
  IF cond2;
    IF cond3;
      EXSR deepNested;
    ENDIF;
  ENDIF;
ENDIF;
```

Mermaid output:
```
IF cond1 --> N2{IF cond2}
N2 --> N3{IF cond3}
N3 --> deepNested
deepNested --> END IF
```

## SELECT with Multiple WHEN

```rpgle
SELECT;
  WHEN status = 'A';
    EXSR processActive;
  WHEN status = 'P';
    EXSR processPending;
  WHEN status = 'C';
    EXSR processComplete;
  OTHER;
    EXSR processUnknown;
ENDSL;
```

## SQLRPGLE Block

```sqlrpgle
     D SQL = 'SELECT CUSTNO, CUSTNAME FROM CUSMST WHERE STATUS = ''A''';
     D                 + ' ORDER BY CUSTNO';
     D                 + ' FETCH FIRST 100 ROWS ONLY';
      /
     C/EXEC SQL
     C+ PREPARE S1 FROM :SQL
     C/END-EXEC
     C/EXEC SQL
     C+ DECLARE C1 CURSOR FOR S1
     C/END-EXEC
     C/EXEC SQL
     C+ OPEN C1
     C/END-EXEC
```

SQL block detected as single node with `sql_count=1`.

## Mixed CL/RPG

```clle
PGM        PARM(&CUSTNO)
DCL        VAR(&CUSTNO) TYPE(*CHAR) LEN(10)
IF         COND(&CUSTNO *EQ ' ') THEN(DO)
SNDPGMMSG  MSG('Customer number required')
RETURN
ENDDO
CALL       PGM(CUSMSTGET) PARM(&CUSTNO)
ENDPGM
```

## Error Handling Pattern

```rpgle
MONITOR;
  CHAIN (k) CUSMST;
  IF %FOUND;
    EXSR processCustomer;
  ELSE;
    EXSR handleNotFound;
  ENDIF;
ON-ERROR 00111;
  EXSR handleIOError;
ON-ERROR 1218;
  EXSR handleLockError;
ON-ERROR *ALL;
  EXSR handleAnyError;
ENDMON;
```
