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

## 我们的部署

- **平台**：Zeabur（`xiaoqiqi.zeabur.app`）
- **传输**：`streamable-http`（MCP 端点 `/mcp`，HTTP 鉴权 `/health` 除外）
- **数据**：Volume 挂载到 `/app/buckets`，重启不丢
- **部署方式**：GitHub push → Zeabur 自动构建 Dockerfile → 重新部署

### 环境变量

| 变量 | 说明 |
|------|------|
| `OMBRE_ADMIN_TOKEN` | 全局鉴权 token（MCP + API 请求需带 `X-Admin-Token` header） |
| `OMBRE_API_KEY` | LLM API 密钥（hold / grow / dream 写入记忆用；只检索可不填） |
| `OMBRE_MCP_KEYS` | 多身份 MCP key：`key1:身份1,key2:身份2`。MCP 请求带 `?key=xxx` 即可路由到对应身份 |
| `OMBRE_TRANSPORT` | `streamable-http`（必设，否则不监听端口） |
| `PORT` | 服务端口（默认 8000） |

### 当前身份配置

`OMBRE_MCP_KEYS` =
```
bunny-ombre-2026:qiqi,keke-ombre-2026:keke,nan_key:nannan
```

| Key | 身份 | 使用者 |
|-----|------|--------|
| `bunny-ombre-2026` | qiqi（柒柒） | qiqi-chat 前端 `?key=bunny-ombre-2026` · 独立 CC 窗口 `?key=bunny-ombre-2026` |
| `keke-ombre-2026` | keke（可可） | 可可的自由时间、nest 论坛 |
| `nan_key` | nannan（楠楠） | 楠楠 CC 窗口 `?key=nan_key` |

> 💡 加新身份只需在 `OMBRE_MCP_KEYS` 末尾追加 `,新key:新名字`，提交部署即可。

---

## 6 个 MCP 工具

| 工具 | 作用 |
|------|------|
| `breath(query, domain, valence, arousal, max_results)` | 浮现/检索记忆。不传参数=自动推送未解决记忆；传 query=关键词+向量双通道检索 |
| `hold(content, tags, importance, feel, source_bucket, ...)` | 存储单条记忆。`feel=True` 写第一人称感受。自动打标+合并相似桶+生成 embedding |
| `grow(content, event_time)` | 日记归档，自动拆分长内容为多个记忆桶 |
| `trace(bucket_id, resolved, protected, highlight, ...)` | 修改元数据、标记已解决、删除。`resolved=1` 让记忆沉底 |
| `pulse(include_archive)` | 查看系统状态 + 记忆桶列表 |
| `dream()` | 做梦——读最近记忆桶，自省消化。有沉淀写 feel，能放下就 resolve |

### AI 使用流程

```
1. breath()              — 睁眼，看有什么浮上来
2. dream()               — 消化最近记忆，有沉淀写 feel
3. breath(domain="feel") — 读之前的 feel
4. 开始和用户说话
```

---

## 接入 Claude Code

### 本地 `.mcp.json` 配置

```json
{
  "mcpServers": {
    "ombre-brain": {
      "type": "streamable-http",
      "url": "https://xiaoqiqi.zeabur.app/mcp?key=nan_key",
      "headers": {
        "X-Admin-Token": "<token>"
      }
    }
  }
}
```

`?key=nan_key` 告诉服务端用哪个身份写记忆。不带 key 则使用默认身份（向后兼容）。

### qiqi-chat 后端直调

qiqi-chat 的 `server.py` 不走 MCP 协议层，直接 HTTP POST JSON-RPC 到 `/mcp`。详见 qiqi-chat 的 `call_mcp_tool()` 函数。

---

## 检索架构

```
breath(query="今天很累")
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

$$final\_score = Importance \times activation\_count^{0.3} \times e^{-\lambda \times days} \times combined\_weight \times resolved\_factor \times urgency\_boost$$

短期（≤3天）：时间 70% + 情感 30% · 长期（>3天）：情感 70% + 时间 30%

---

## 更新部署

```bash
cd OmbreBrain-folio
git pull origin main
git push origin main    # Zeabur 自动重新部署
```

Volume 挂载的记忆数据不受影响。

---

## License

本项目基于上游 [P0luz/Ombre-Brain](https://github.com/P0luz/Ombre-Brain) 的开源许可。详见 LICENSE 文件。
