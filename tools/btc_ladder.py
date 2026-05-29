#!/usr/bin/env python3
"""
btc_ladder.py — 个人 BTC 分批进出执行表 (counter-cyclical accumulation planner)

设计原则 (来自对本仓库 6 年真实账本的复盘):
  - 越跌越接 (back-weighted 加仓阶梯), 越涨越减 (按账本里 '净多比例 vs 价格' 斜率校准)
  - 零杠杆, 盯 BTC 张数不盯美元浮亏, 按价格档触发而非按预测触发
  - 核心仓永不卖; 只用战术仓 + 干火药做循环

用法:
  python3 tools/btc_ladder.py --price 73722
  python3 tools/btc_ladder.py --price 64000 --config tools/btc_plan_config.json

配置文件 (JSON) 字段见 btc_plan_config.example.json。
注意: 真实资金请放在被 .gitignore 的 btc_plan_config.json 里, 不要提交到公开仓库。

这不是投资建议。价格档是预设触发点, 不是预测。风险自担。
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path):
    if not os.path.exists(path):
        sys.exit(f"找不到配置文件: {path}\n先复制 btc_plan_config.example.json 为 btc_plan_config.json 并填入你的数字。")
    with open(path) as f:
        return json.load(f)


def fmt_usd(x):
    return f"${x:,.0f}"


def buy_table(cfg, price):
    dp = cfg["dry_powder_usd"]
    executed = cfg.get("executed_buys", [])
    exec_prices = {e["price"] for e in executed}
    spent = sum(e["usd"] for e in executed)
    got_btc = sum(e["usd"] / e["price"] for e in executed)

    print("=" * 78)
    print(f"📉 加仓阶梯   干火药 {fmt_usd(dp)}   当前价 {fmt_usd(price)}", end="")
    if cfg.get("cycle_high"):
        dd = price / cfg["cycle_high"] - 1
        print(f"   (距顶 {fmt_usd(cfg['cycle_high'])}: {dd*100:+.0f}%)")
    else:
        print()
    print("=" * 78)
    print(f"{'档位价':>9} {'距顶':>6} {'投入$':>10} {'占DP':>6} {'该档BTC':>9}  状态")
    print("-" * 78)
    plan_usd, plan_btc = spent, got_btc
    for r in cfg["buy_ladder"]:
        rp, pct = r["price"], r["pct"]
        usd = dp * pct
        btc = usd / rp
        dd = f"{(rp/cfg['cycle_high']-1)*100:+.0f}%" if cfg.get("cycle_high") else "—"
        if rp in exec_prices:
            status = "☑ 已执行"
        elif price <= rp:
            status = "🟢 已进区间 → 现在可动"
            plan_usd += usd; plan_btc += btc
        else:
            status = f"⏳ 等待 (需再跌 {(price/rp-1)*-100:.0f}% 到 {fmt_usd(rp)})"
            plan_usd += usd; plan_btc += btc
        print(f"{fmt_usd(rp):>9} {dd:>6} {usd:>10,.0f} {pct*100:>5.0f}% {btc:>9.4f}  {status}")
    print("-" * 78)
    if got_btc > 0:
        print(f"已投入 {fmt_usd(spent)} → 已得 {got_btc:.4f} BTC (均价 {fmt_usd(spent/got_btc)})")
    print(f"剩余弹药 {fmt_usd(dp - spent)}")
    if plan_btc > 0:
        print(f"若按表全部投完: 共 {plan_btc:.4f} BTC, 综合成本 {fmt_usd(plan_usd/plan_btc)}")
        lump = dp / price
        print(f"对比现在一把梭哈 @ {fmt_usd(price)}: 仅 {lump:.4f} BTC  →  阶梯多攒 {plan_btc-lump:+.4f} BTC "
              f"({(plan_btc/lump-1)*100:+.0f}%, 前提是真跌下去)")
    print()


def trim_table(cfg, price):
    core = cfg.get("core_btc", 0.0)
    current = cfg.get("current_btc", 0.0)
    tactical = max(current - core, 0.0)
    print("=" * 78)
    print(f"📈 减仓阶梯   现有 {current:.4f} BTC = 核心(永不卖) {core:.4f} + 战术 {tactical:.4f}")
    print("   (按账本里 '价格越高净多比例越低' 校准, 减下来的钱回补干火药)")
    print("=" * 78)
    print(f"{'触发价':>9} {'减战术仓%':>9} {'卖出BTC':>9} {'约收回$':>11}  状态")
    print("-" * 78)
    remaining = tactical
    for r in cfg.get("trim_ladder", []):
        tp = r["price"]; pct = r["trim_pct_of_tactical"]
        sell = remaining * pct
        cash = sell * tp
        status = "🔴 已到/超过 → 可减" if price >= tp else f"⏳ 等待 (需涨到 {fmt_usd(tp)})"
        print(f"{fmt_usd(tp):>9} {pct*100:>8.0f}% {sell:>9.4f} {cash:>11,.0f}  {status}")
        remaining -= sell
    print("-" * 78)
    print()


def main():
    ap = argparse.ArgumentParser(description="个人 BTC 分批进出执行表")
    ap.add_argument("--price", type=float, required=True, help="当前 BTC 价格 (USD)")
    ap.add_argument("--config", default=os.path.join(HERE, "btc_plan_config.json"))
    args = ap.parse_args()
    cfg = load_config(args.config)

    pct_sum = sum(r["pct"] for r in cfg["buy_ladder"])
    if abs(pct_sum - 1.0) > 0.001:
        print(f"⚠️  buy_ladder 各档百分比之和 = {pct_sum*100:.0f}% (不是 100%, 请检查配置)\n")

    print()
    buy_table(cfg, args.price)
    if cfg.get("current_btc"):
        trim_table(cfg, args.price)
    print("🧱 铁律: 零杠杆 · 仓位扛得住到极端价不被迫卖 · 按价格档触发不按预测触发 · 盯张数")
    print("⚠️  非投资建议; 价格档是预设触发点不是预测; 风险自担。")
    print()


if __name__ == "__main__":
    main()
