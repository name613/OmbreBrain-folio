# Ombre Brain · 海马体

一个给 AI 用的长期情绪记忆系统。基于 Russell 效价/唤醒度坐标打标，带遗忘曲线和向量语义检索，通过 MCP 接入 Claude Code。

> ### 开源声明
> 本项目 fork 自 **[ceshihaox-dotcom/OmbreBrain-folio](https://github.com/ceshihaox-dotcom/OmbreBrain-folio)**（第一版优化分支），
> 其上追 **[P0luz/Ombre-Brain](https://github.com/P0luz/Ombre-Brain)**（原作者），均已获授权开源。
>
> 基础衰减、做梦、feel 与 Markdown 记忆桶保持上游兼容；本仓另加了身份隔离、类型化检索和独立牵引状态。
> 第一版 fork 主要做了前端体验、便利功能、中文检索精度优化（详见 [CHANGES.md](./CHANGES.md)）。
> 本仓在此基础上做了：多身份 MCP key 路由、URL key 身份注入、简化部署配置。
>
> 📋 [CHANGES.md](./CHANGES.md) · 🚀 [DEPLOY.md](./DEPLOY.md) · 🔄 [MIGRATION.md](./MIGRATION.md)

---

## 部署

- **平台**：Zeabur
- **传输**：`streamable-http`（MCP 端点 `/mcp`，`/health` 免鉴权）
- **数据**：Volume 挂载到 `/app/buckets`，重启不丢
- **部署方式**：GitHub push → Zeabur 自动构建 Dockerfile → 重新部署

### 关键环境变量

| 变量 | 说明 |
|------|------|
| `OMBRE_ADMIN_TOKEN` | 全局鉴权 token（MCP + API 请求需带 `X-Admin-Token` header） |
| `OMBRE_API_KEY` | LLM API 密钥（hold / grow / dream 写入记忆用；只检索可不填） |
| `OMBRE_MCP_KEYS` | 多身份 MCP key：`key1:身份名,key2:身份名`。MCP 请求带 `?key=xxx` 即可路由到对应身份 |
| `OMBRE_TRANSPORT` | 设为 `streamable-http`（必设，否则不监听端口） |
| `PORT` | 服务端口（默认 8000） |

### 多身份配置

`OMBRE_MCP_KEYS` 格式：`your-key-1:name1,your-key-2:name2`

添加新身份只需追加 `,new-key:new-name`，push 部署即可。各 AI / 用户使用不同的 `?key=` 参数连接 MCP，记忆写入时自动带上对应身份标签，breath 检索互不干扰。

---

## 7 个 MCP 工具

| 工具 | 作用 |
|------|------|
| `breath(query, domain, memory_kind, ...)` | 浮现/检索记忆；可只查事实、操作方法、约定等类型 |
| `hold(content, memory_kind, subject, ...)` | 存储单条记忆；自动识别记忆类型与主体，`feel=True` 仍写独立感受层 |
| `grow(content, event_time)` | 日记归档，自动拆分长内容为多个记忆桶 |
| `trace(bucket_id, resolved, protected, highlight, ...)` | 修改元数据、标记已解决、删除 |
| `pulse(include_archive)` | 查看系统状态 + 记忆桶列表 |
| `dream()` | 做梦——读最近记忆桶，自省消化 |
| `yearn(action, title, tension, priority, ...)` | 管理当前身份的持续牵引；独立存储，不污染普通记忆和向量检索 |

### 类型化检索与身份隔离

新记忆可标为 `fact`、`procedure`、`commitment`、`preference`、`relationship`、`episode`、`reflection` 或 `desire`。技术/配置类查询会优先事实与操作方法，降低纯反思内容的排名；旧记忆没有该字段时保持原行为。

命名 AI 身份以 `created_by` 为所有权依据，即使对应 MCP key 暂时从环境变量移除，也不会自动变成共享记忆。历史 `ai`、`user`、`import` 和无所有者记忆保持共享兼容。

`breath(domain="feel")` 会为每条旧感受标注距今天数，并明确它是过去经历的证据、不是当前情绪指令，避免模型把旧情绪直接续写成“此刻仍然如此”。

### 持续牵引的边界

`yearn` 当前是一个轻量的愿望/目标层：记录“想做什么、为什么、牵引有多强、进展到哪里”，并按身份独立保存。它不是完整的自主驱动或事件情绪引擎，不会自行修改数值、触发行动或替 AI 规定感受。每条记录在身份分区之外还保存 `owner`，读取和修改时做第二次所有权校验。

管理前端在“设置 → 欲望与牵引”提供跨身份的只读观察窗，也可从桌面导航的“牵引”进入。前端不提供新建、修改、完成或删除入口；每个身份只能通过自己的 MCP `yearn` 工具维护自身牵引。

### 设计参考与取舍

- [P0luz/Ombre-Brain](https://github.com/P0luz/Ombre-Brain)：原始记忆桶、衰减、feel、dream 与 MCP 基础。
- [ceshihaox-dotcom/OmbreBrain-folio](https://github.com/ceshihaox-dotcom/OmbreBrain-folio)：本仓直接 fork 的前端与中文检索优化基础。
- [Yinglianchun/Ombre-Brain](https://github.com/Yinglianchun/Ombre-Brain)：作为架构参考，重点比较了身份锚点、原始事件、写入门和 Gateway 思路；本轮代码按 folio 现有结构独立实现，没有直接合并该仓代码。
- 社区讨论 `T1689`（自动捕获与注入接口）、`T2212`（时间锚与分层记忆）、`T2223`（事件情绪、身份私产与旧感受时间透镜）以及 Galatea Garden 的长期使用反馈，帮助确定了“背景而非台词、事实与感受分层、状态按身份隔离”的原则。

原始事件黑匣子、候选写入层和客户端自动注入 hook 适合放在下一阶段：它们需要幂等、失败重试、隐私授权和客户端兼容性一起设计，暂不与这次低风险升级捆绑部署。

### 推荐使用流程

```
breath() → dream() → breath(domain="feel") → 开始对话
```

---

## 接入 Claude Code

在 `.mcp.json` 中配置：

```json
{
  "mcpServers": {
    "ombre-brain": {
      "type": "streamable-http",
      "url": "https://<your-domain>/mcp?key=<your-key>",
      "headers": {
        "X-Admin-Token": "<your-admin-token>"
      }
    }
  }
}
```

`?key=` 参数告诉服务端用哪个身份读写记忆。不带 key 则使用默认身份（向后兼容）。

---

## 检索架构

```
breath(query)
         │
    ┌────┴────┐
    │         │
 关键词匹配   向量语义
 (rapidfuzz)  (cosine similarity)
    │         │
    └────┬────┘
         │
    去重 + 合并
    token 预算截断
         │
    返回 ≤20 条结果
```

---

## 衰减公式（与上游一致）

短期（≤3天）：时间 70% + 情感 30% · 长期（>3天）：情感 70% + 时间 30%

---

## 更新部署

```bash
git pull origin main && git push origin main
```

Volume 挂载的记忆数据不受影响。

---

## License

本项目基于上游 [P0luz/Ombre-Brain](https://github.com/P0luz/Ombre-Brain) 的开源许可。详见 LICENSE 文件。
