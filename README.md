# Ombre Brain · 海马体

一个给 AI 用的长期情绪记忆系统。基于 Russell 效价/唤醒度坐标打标，带遗忘曲线和向量语义检索，通过 MCP 接入 Claude Code。

> ### 开源声明
> 本项目 fork 自 **[ceshihaox-dotcom/OmbreBrain-folio](https://github.com/ceshihaox-dotcom/OmbreBrain-folio)**（第一版优化分支），
> 其上追 **[P0luz/Ombre-Brain](https://github.com/P0luz/Ombre-Brain)**（原作者），均已获授权开源。
>
> **核心记忆机制（衰减公式 / 做梦 / feel / 记忆桶 / 情感权重）与原作者完全一致、未改动。**
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

## 6 个 MCP 工具

| 工具 | 作用 |
|------|------|
| `breath(query, domain, valence, arousal, max_results)` | 浮现/检索记忆。不传参数=自动推送未解决记忆；传 query=关键词+向量双通道检索 |
| `hold(content, tags, importance, feel, source_bucket, ...)` | 存储单条记忆。`feel=True` 写第一人称感受。自动打标+合并相似桶+生成 embedding |
| `grow(content, event_time)` | 日记归档，自动拆分长内容为多个记忆桶 |
| `trace(bucket_id, resolved, protected, highlight, ...)` | 修改元数据、标记已解决、删除 |
| `pulse(include_archive)` | 查看系统状态 + 记忆桶列表 |
| `dream()` | 做梦——读最近记忆桶，自省消化 |

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
