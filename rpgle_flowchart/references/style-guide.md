# Output Style Guide

## Mermaid Theme Options

### Default (Light)
```
flowchart TD
    %% No theme declaration
```

### Dark Theme
```mermaid
%%{init: {'theme':'dark','themeVariables':{'primaryColor':'#1f2937','primaryTextColor':'#f9fafb','lineColor':'#93c5fd','secondaryColor':'#111827','tertiaryColor':'#374151'}}}%%
flowchart TD
```

### Pastel Theme
```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#dbeafe','primaryTextColor':'#111827','lineColor':'#60a5fa','secondaryColor':'#fde68a','tertiaryColor':'#fbcfe8'}}}%%
flowchart TD
```

## Node Shapes

| Shape | Mermaid Syntax | Use Case |
|-------|---------------|----------|
| Process | `A[Label]` | Normal statements |
| Decision | `A{Decision?}` | IF/Select conditions |
| Terminal | `A([Start/End])` | Program entry/exit |
| I/O | `A[/Input/]` | CHAIN/READ/WRITE |
| SQL | `A[(SQL)]` | SQL operations |

## Color Coding

Recommended custom colors for AS400 entities:

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#e0f2fe',
  'primaryTextColor': '#0c4a6e',
  'lineColor': '#0284c7',
  'secondaryColor': '#f0fdf4',
  'tertiaryColor': '#fef3c7'
}}}%%
```

## Layout Hints

### Left-to-Right Flow
```mermaid
flowchart LR
```

### Top-to-Bottom Flow (default)
```mermaid
flowchart TD
```

## Subgraph Naming

| Group | Subgraph Name | Color |
|-------|---------------|-------|
| MAIN | MAIN | Default |
| Subroutine | SR:ROUTINENAME | Yellow |
| Procedure | PROC:PROCNAME | Blue |
