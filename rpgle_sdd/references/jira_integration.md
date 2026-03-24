# Jira/Confluence 集成指南

## Jira 集成

### 环境变量配置

```bash
export JIRA_URL="https://jira.company.com"
export JIRA_TOKEN="your-api-token"
export JIRA_PROJECT="PROJ"
```

### 获取 API Token

1. 登录 Jira
2. 进入 Account Settings → Security
3. 创建 API Token
4. 使用 email:token 认证

### 使用示例

```bash
# 获取单个 Story
python3 scripts/fetch_jira.py JIRA-123

# 批量获取
python3 scripts/fetch_jira.py --epic JIRA-100

# 导出 Sprint Stories
python3 scripts/fetch_jira.py --sprint 123
```

### 输出格式

```json
{
  "key": "JIRA-123",
  "summary": "Story summary",
  "description": "Full description",
  "acceptance_criteria": ["Criteria 1", "Criteria 2"],
  "linked_issues": ["JIRA-100", "JIRA-101"],
  "attachments": ["file1.pdf"]
}
```

## Confluence 集成

### 环境变量配置

```bash
export CONFLUENCE_URL="https://confluence.company.com"
export CONFLUENCE_USER="email@company.com"
export CONFLUENCE_TOKEN="your-api-token"
```

### 使用示例

```bash
# 获取页面内容
python3 scripts/fetch_confluence.py 12345

# 搜索页面
python3 scripts/fetch_confluence.py --search "AS400 规范"

# 导出页面为 Markdown
python3 scripts/fetch_confluence.py 12345 --format markdown
```

## 错误处理

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| 401 | 认证失败 | 检查 token |
| 403 | 权限不足 | 联系管理员 |
| 404 | 资源不存在 | 检查 ID |
| 429 | 请求频率超限 | 降低频率 |
| 500 | 服务器错误 | 重试 |

## 本地模拟

如果没有 Jira/Confluence 环境，可以使用本地文件：

```bash
# Story 保存在 story.txt
python3 scripts/sdd_generator.py --story "$(cat story.txt)"
```

---

_集成测试通过后，更新环境变量配置。_
