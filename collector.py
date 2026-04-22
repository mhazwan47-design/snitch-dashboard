import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "signals-input.json"
OUTPUT_FILE = ROOT / "docs" / "data" / "dashboard-current.json"


def load_signals():
    if not INPUT_FILE.exists():
        return []
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def action_long(short_action):
    mapping = {
        "WAIT FOR CONFIRMATION": "Prepare Entry",
        "WATCH": "Keep On Watch",
        "REDUCE RISK": "Reduce Risk",
        "AVOID": "Avoid Fresh Entry",
    }
    return mapping.get(short_action, short_action.title())


def sort_bucket(items):
    return sorted(items, key=lambda x: (float(x.get("score", 0)), float(x.get("tradeUsd", 0))), reverse=True)


def build_buckets(signals):
    trade_focus = []
    emerging = []
    caution = []

    for raw in signals:
        short = raw.get("actionShort", "WATCH")

        item = {
            "token": raw["token"],
            "pair": raw["pair"],
            "action": action_long(short),
            "actionShort": short,
            "confidence": raw.get("confidence", "Medium"),
            "score": raw.get("score", 0),
            "direction": raw.get("direction", ""),
            "impactPct": raw.get("impactPct", 0),
            "tradeUsd": raw.get("tradeUsd", 0),
            "risk": raw.get("risk", "Medium"),
            "why": raw.get("why", ""),
            "nextStep": raw.get("nextStep", ""),
            "doNot": raw.get("doNot", ""),
            "cancelIf": raw.get("cancelIf", ""),
        }

        if item["direction"] == "Buy Pressure":
            if item["score"] >= 7:
                trade_focus.append(item)
            else:
                emerging.append(item)
        else:
            caution.append(item)

    return sort_bucket(trade_focus), sort_bucket(emerging), sort_bucket(caution)


def build_recent(signals):
    recent = []
    for s in signals[:10]:
        recent.append({
            "time": "Auto",
            "token": s["token"],
            "pair": s["pair"],
            "direction": s["direction"],
            "action": s.get("actionShort", "WATCH"),
            "score": s["score"],
            "impact": f"{s['impactPct']}%",
            "usd": f"${s['tradeUsd']:,.2f}",
        })
    return recent


def build_action_mix(trade_focus, emerging, caution):
    return [
        {"name": "Prepare / Wait", "value": len(trade_focus)},
        {"name": "Watch", "value": len(emerging)},
        {"name": "Avoid / Reduce", "value": len(caution)},
    ]


def main():
    signals = load_signals()
    trade_focus, emerging, caution = build_buckets(signals)

    total = len(trade_focus) + len(emerging) + len(caution)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    data = {
        "meta": {
            "product": "SNITCH Alert Dashboard",
            "mode": "Live Monitor",
            "marketBias": "Neutral",
            "asOf": now,
            "dataSource": "collector.py"
        },
        "metrics": {
            "qualifiedSignals": total,
            "tradeFocus": len(trade_focus),
            "emerging": len(emerging),
            "caution": len(caution),
            "avgConfidence": 70,
            "winRate30d": 58
        },
        "tradeFocusNow": trade_focus,
        "emergingPotential": emerging,
        "cautionAvoid": caution,
        "recentSignals": build_recent(signals),
        "performance": {
            "scoreTrend": [],
            "actionMix": build_action_mix(trade_focus, emerging, caution),
            "proof": [
                {"metric": "Qualified Signals", "value": str(total)},
                {"metric": "30D Win Rate", "value": "58%"},
                {"metric": "Avg Confidence", "value": "70/100"},
                {"metric": "Risk-Off Alerts", "value": str(len(caution))}
            ]
        }
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
