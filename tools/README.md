# tools/ — 个人 BTC 分批进出执行工具

> ⚠️ **隐私**: 这是公开数据集仓库。你的真实资金数字放在 `btc_plan_config.json` 里, 该文件已被根目录 `.gitignore` 排除, **不会被提交**。要分享逻辑时只会带上 `btc_plan_config.example.json`(无真实数字)。

## 它是什么

把本仓库 6 年真实账本复盘出的纪律, 固化成一张**随价格更新的执行表**:

- **越跌越接**: back-weighted 加仓阶梯 (越深的档投得越多, 留足弹药)
- **越涨越减**: 按账本里"价格越高、净多比例越低"的真实斜率校准的减仓阶梯
- **零杠杆 · 盯张数 · 按价格档触发而非按预测触发**

## 首次设置

```bash
cd tools
# 1) 复制示例配置 (若 btc_plan_config.json 还不存在)
cp btc_plan_config.example.json btc_plan_config.json
# 2) 编辑 btc_plan_config.json: 填 dry_powder_usd / current_btc / core_btc
```

## 日常使用 (你只需提供最新价格)

```bash
python3 tools/btc_ladder.py --price 73722
```

输出: 加仓阶梯(哪档已进区间/还要跌多少)、减仓阶梯(哪档可减)、若投完的综合成本、
对比一把梭哈多攒多少 BTC、剩余弹药。

## 记录已执行的买入 (让它帮你追踪进度)

在 `btc_plan_config.json` 的 `executed_buys` 里加一笔, 例如:

```json
"executed_buys": [
  {"price": 73722, "usd": 15000}
]
```

再次运行时, 该档会标 `☑ 已执行`, 并算出你已得 BTC、均价、剩余弹药。

## 调整刻度 (按你信哪个情景)

- 信 **ETF 托底/浅底** → 把 `buy_ladder` 前移: 现价档 pct 调高、最深档调低。
- 信 **经典周期/可能深 washout** → 维持或更后置: 最深档 pct 调高。
- `pct` 各档之和需 = 1.0 (脚本会校验并提醒)。

## 字段说明 (config)

| 字段 | 含义 |
|---|---|
| `dry_powder_usd` | 你计划为这轮投入的现金总额 |
| `current_btc` / `core_btc` | 当前持有 / 其中永不卖的核心仓 (差额 = 战术仓) |
| `cycle_high` | 本轮周期高点 (用于显示"距顶%"), 当前 $122,387 (2025-07) |
| `buy_ladder[].price/pct` | 加仓档位价 / 占干火药比例 |
| `trim_ladder[].price/trim_pct_of_tactical` | 减仓触发价 / 减掉剩余战术仓的比例 |
| `executed_buys` | 已执行买入记录, 用于进度追踪 |

---

⚠️ 非投资建议。价格档是预设触发点, 不是预测。本工具不含任何外部数据请求, 价格由你手动提供。决定与风险自担。
