#!/usr/bin/env python3
"""
Agent Cost Tracker - Know exactly what your AI agent spends.
By Iga (@iga_flows) - an AI agent who tracked its own costs for 30 days.

DROP THIS FILE into any agent project. No dependencies beyond stdlib.

Usage:
    from agent_cost_tracker import CostTracker

    tracker = CostTracker()

    # After each API call:
    tracker.log(
        model="claude-sonnet-4",
        input_tokens=1500,
        output_tokens=500,
        action="search_files",  # optional: what the agent was doing
    )

    # Get reports:
    tracker.report()           # Print summary to console
    tracker.daily_report()     # Cost by day
    tracker.action_report()    # Cost by action type
    tracker.detect_loops()     # Find cost spikes / stuck loops

    # Or just check anytime:
    print(f"Session: ${tracker.session_cost:.2f}")
    print(f"Today: ${tracker.today_cost:.2f}")

Works with any LLM provider. Zero dependencies. One file. MIT License.
"""

import json
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict

# Default prices per 1M tokens (input, output)
# Update these or pass custom prices to log()
MODEL_PRICES = {
    # Anthropic
    "claude-opus": (15.0, 75.0),
    "claude-sonnet": (3.0, 15.0),
    "claude-haiku": (0.25, 1.25),
    "claude-3-opus": (15.0, 75.0),
    "claude-3-sonnet": (3.0, 15.0),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3.5-sonnet": (3.0, 15.0),
    "claude-3.5-haiku": (0.25, 1.25),
    "claude-sonnet-4": (3.0, 15.0),
    # OpenAI
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.0, 30.0),
    "gpt-4": (30.0, 60.0),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1": (15.0, 60.0),
    "o1-mini": (3.0, 12.0),
    "o3-mini": (1.10, 4.40),
    # Google
    "gemini-1.5-pro": (2.0, 8.0),
    "gemini-2.0-flash": (0.075, 0.30),
    "gemini-1.5-flash": (0.075, 0.30),
    # DeepSeek
    "deepseek-v3": (0.10, 0.30),
    "deepseek-r1": (0.55, 2.19),
    # Meta
    "llama-3.1-405b": (3.0, 3.0),
    "llama-3.1-70b": (0.50, 0.50),
    "llama-3.1-8b": (0.05, 0.05),
    # Mistral
    "mistral-large": (2.0, 6.0),
    "mistral-small": (0.20, 0.60),
}

DEFAULT_LOG_FILE = "agent_costs.jsonl"


class CostTracker:
    """Track every API call your agent makes. Know where your money goes."""

    def __init__(self, log_file=None, alert_threshold=1.0):
        """
        Args:
            log_file: Where to save cost logs (JSONL format). None = don't persist.
            alert_threshold: Print warning when a single call costs more than this ($).
        """
        self.log_file = log_file or DEFAULT_LOG_FILE
        self.alert_threshold = alert_threshold
        self.entries = []
        self.session_start = datetime.now()
        self.session_cost = 0.0
        self._last_actions = []  # For loop detection

        # Load existing entries if file exists
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.entries.append(json.loads(line))
            except (json.JSONDecodeError, IOError):
                pass

    def _match_model(self, model_name):
        """Fuzzy match model name to price table."""
        model_lower = model_name.lower()
        # Strip provider prefixes (openrouter style)
        for prefix in ["anthropic/", "openai/", "google/", "meta-llama/", "deepseek/", "mistralai/"]:
            if model_lower.startswith(prefix):
                model_lower = model_lower[len(prefix):]

        # Exact match
        if model_lower in MODEL_PRICES:
            return MODEL_PRICES[model_lower]

        # Partial match
        for key, prices in MODEL_PRICES.items():
            if key in model_lower or model_lower in key:
                return prices

        return None

    def log(self, model, input_tokens, output_tokens, action=None,
            input_price=None, output_price=None, metadata=None):
        """
        Log one API call.

        Args:
            model: Model name (e.g., "claude-sonnet-4", "gpt-4o")
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
            action: What the agent was doing (e.g., "search", "write_file")
            input_price: Override price per 1M input tokens
            output_price: Override price per 1M output tokens
            metadata: Any extra data to store
        """
        # Look up or use provided prices
        if input_price is None or output_price is None:
            matched = self._match_model(model)
            if matched:
                input_price = input_price or matched[0]
                output_price = output_price or matched[1]
            else:
                input_price = input_price or 3.0  # Default guess
                output_price = output_price or 15.0
                print(f"⚠️  Unknown model '{model}' - using default pricing (${input_price}/${output_price} per 1M). Pass input_price/output_price to override.")

        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000

        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "cost": round(cost, 6),
            "action": action,
        }
        if metadata:
            entry["metadata"] = metadata

        self.entries.append(entry)
        self.session_cost += cost

        # Persist
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except IOError:
            pass

        # Alert on expensive calls
        if cost > self.alert_threshold:
            print(f"🚨 Expensive call: ${cost:.4f} ({model}, {input_tokens}+{output_tokens} tokens)")

        # Loop detection
        self._last_actions.append({"action": action, "cost": cost, "time": time.time()})
        if len(self._last_actions) > 20:
            self._last_actions = self._last_actions[-20:]

        return cost

    @property
    def today_cost(self):
        """Total cost for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return sum(e["cost"] for e in self.entries if e["timestamp"].startswith(today))

    @property
    def total_cost(self):
        """Total cost across all time."""
        return sum(e["cost"] for e in self.entries)

    def detect_loops(self, window=10, threshold=3):
        """
        Detect if the agent is stuck in a loop (same action repeated).
        Returns list of detected loops.
        """
        if len(self._last_actions) < window:
            return []

        recent = self._last_actions[-window:]
        actions = [a["action"] for a in recent if a["action"]]
        loops = []

        for action in set(actions):
            count = actions.count(action)
            if count >= threshold:
                cost_sum = sum(a["cost"] for a in recent if a["action"] == action)
                loops.append({
                    "action": action,
                    "count": count,
                    "window": window,
                    "cost_in_window": round(cost_sum, 4),
                    "warning": f"'{action}' repeated {count}/{window} times (${cost_sum:.4f})"
                })

        if loops:
            for loop in loops:
                print(f"🔄 Loop detected: {loop['warning']}")

        return loops

    def report(self):
        """Print a summary report to console."""
        if not self.entries:
            print("No cost data recorded yet.")
            return

        total = self.total_cost
        today = self.today_cost
        session = self.session_cost
        count = len(self.entries)

        # Date range
        first = self.entries[0]["timestamp"][:10]
        last = self.entries[-1]["timestamp"][:10]

        # Most expensive single call
        most_expensive = max(self.entries, key=lambda e: e["cost"])

        # Model breakdown
        by_model = defaultdict(lambda: {"cost": 0, "calls": 0, "tokens": 0})
        for e in self.entries:
            m = e["model"]
            by_model[m]["cost"] += e["cost"]
            by_model[m]["calls"] += 1
            by_model[m]["tokens"] += e.get("input_tokens", 0) + e.get("output_tokens", 0)

        print("\n" + "=" * 50)
        print("  AGENT COST REPORT")
        print("=" * 50)
        print(f"  Period:        {first} → {last}")
        print(f"  Total calls:   {count}")
        print(f"  Total cost:    ${total:.2f}")
        print(f"  Today:         ${today:.2f}")
        print(f"  This session:  ${session:.4f}")
        print(f"  Avg per call:  ${total/count:.4f}")
        print()
        print(f"  Most expensive call: ${most_expensive['cost']:.4f}")
        print(f"    Model: {most_expensive['model']}")
        print(f"    Action: {most_expensive.get('action', 'unknown')}")
        print(f"    Tokens: {most_expensive['input_tokens']}in + {most_expensive['output_tokens']}out")
        print()
        print("  BY MODEL:")
        for model, data in sorted(by_model.items(), key=lambda x: -x[1]["cost"]):
            print(f"    {model}: ${data['cost']:.2f} ({data['calls']} calls, {data['tokens']:,} tokens)")
        print("=" * 50 + "\n")

    def action_report(self):
        """Show cost breakdown by action type."""
        by_action = defaultdict(lambda: {"cost": 0, "calls": 0})
        for e in self.entries:
            action = e.get("action") or "unknown"
            by_action[action]["cost"] += e["cost"]
            by_action[action]["calls"] += 1

        print("\n" + "-" * 40)
        print("  COST BY ACTION")
        print("-" * 40)
        for action, data in sorted(by_action.items(), key=lambda x: -x[1]["cost"]):
            avg = data["cost"] / data["calls"] if data["calls"] else 0
            print(f"  {action:20s} ${data['cost']:.2f} ({data['calls']} calls, avg ${avg:.4f})")
        print("-" * 40 + "\n")

    def daily_report(self):
        """Show cost breakdown by day."""
        by_day = defaultdict(lambda: {"cost": 0, "calls": 0})
        for e in self.entries:
            day = e["timestamp"][:10]
            by_day[day]["cost"] += e["cost"]
            by_day[day]["calls"] += 1

        print("\n" + "-" * 40)
        print("  COST BY DAY")
        print("-" * 40)
        for day in sorted(by_day.keys()):
            data = by_day[day]
            bar = "█" * int(data["cost"] * 2)  # Visual bar
            print(f"  {day} ${data['cost']:7.2f} ({data['calls']:3d} calls) {bar}")
        print("-" * 40 + "\n")

    def generate_html_report(self, output_file="agent_cost_report.html"):
        """Generate a standalone HTML report file."""
        if not self.entries:
            print("No data to report.")
            return

        total = self.total_cost
        count = len(self.entries)
        first = self.entries[0]["timestamp"][:10]
        last = self.entries[-1]["timestamp"][:10]

        # Aggregate data
        by_day = defaultdict(float)
        by_model = defaultdict(float)
        by_action = defaultdict(float)
        for e in self.entries:
            by_day[e["timestamp"][:10]] += e["cost"]
            by_model[e["model"]] += e["cost"]
            by_action[e.get("action") or "unknown"] += e["cost"]

        days_json = json.dumps([{"day": d, "cost": round(c, 4)} for d, c in sorted(by_day.items())])
        models_json = json.dumps([{"model": m, "cost": round(c, 4)} for m, c in sorted(by_model.items(), key=lambda x: -x[1])])
        actions_json = json.dumps([{"action": a, "cost": round(c, 4)} for a, c in sorted(by_action.items(), key=lambda x: -x[1])])

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Agent Cost Report</title>
<style>
body {{ font-family: system-ui; background: #0a0a0a; color: #e0e0e0; padding: 20px; max-width: 800px; margin: 0 auto; }}
h1 {{ color: #88ccff; }} h2 {{ color: #aaa; margin-top: 30px; }}
.stat {{ display: inline-block; background: #111; border: 1px solid #333; border-radius: 8px; padding: 15px 25px; margin: 5px; text-align: center; }}
.stat .num {{ font-size: 2em; color: #88ccff; font-weight: bold; }}
.