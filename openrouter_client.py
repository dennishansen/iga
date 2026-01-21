"""
OpenRouter API client - drop-in replacement for Anthropic SDK
Provides cost tracking and budget management
"""
import os
import json
from openai import OpenAI
from datetime import datetime

# Initialize OpenRouter client (OpenAI-compatible)
_client = None
_daily_cost = 0.0
_cost_log_file = "data/openrouter_costs.json"

def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
    return _client

def load_cost_log():
    """Load cost tracking data"""
    try:
        with open(_cost_log_file, 'r') as f:
            return json.load(f)
    except:
        return {"total": 0.0, "daily": {}, "requests": []}

def save_cost_log(data):
    """Save cost tracking data"""
    os.makedirs(os.path.dirname(_cost_log_file), exist_ok=True)
    with open(_cost_log_file, 'w') as f:
        json.dump(data, f, indent=2)

def log_cost(cost, model, tokens_in, tokens_out):
    """Log a request's cost"""
    data = load_cost_log()
    today = datetime.now().strftime("%Y-%m-%d")
    
    data["total"] += cost
    data["daily"][today] = data["daily"].get(today, 0.0) + cost
    data["requests"].append({
        "time": datetime.now().isoformat(),
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost
    })
    
    # Keep only last 1000 requests
    if len(data["requests"]) > 1000:
        data["requests"] = data["requests"][-1000:]
    
    save_cost_log(data)
    return data["daily"][today]

def chat(model, system, messages, max_tokens=2048):
    """
    Make a chat completion request via OpenRouter
    Returns (content, usage_info)
    """
    client = get_client()
    
    # Convert Anthropic-style messages to OpenAI format
    openai_messages = []
    if system:
        openai_messages.append({"role": "system", "content": system})
    openai_messages.extend(messages)
    
    response = client.chat.completions.create(
        model=model,
        messages=openai_messages,
        max_tokens=max_tokens,
        timeout=120,  # 2 minute timeout to prevent hanging
        extra_headers={
            "HTTP-Referer": "https://github.com/iga",
            "X-Title": "Iga Autonomous Agent"
        }
    )
    
    # Extract content
    content = response.choices[0].message.content
    
    # Extract usage
    usage = response.usage
    tokens_in = usage.prompt_tokens if usage else 0
    tokens_out = usage.completion_tokens if usage else 0
    
    # OpenRouter includes cost in response (if available)
    # Estimate otherwise based on opus-4.5 pricing
    cost = getattr(response, 'cost', None)
    if cost is None:
        # Estimate: $5/1M input, $25/1M output for opus-4.5
        cost = (tokens_in * 5 / 1_000_000) + (tokens_out * 25 / 1_000_000)
    
    daily_cost = log_cost(cost, model, tokens_in, tokens_out)
    
    return content, {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
        "daily_cost": daily_cost
    }

def get_daily_cost():
    """Get today's spending"""
    data = load_cost_log()
    today = datetime.now().strftime("%Y-%m-%d")
    return data["daily"].get(today, 0.0)

def get_total_cost():
    """Get all-time spending"""
    data = load_cost_log()
    return data["total"]

if __name__ == "__main__":
    # Test
    print(f"Daily cost: ${get_daily_cost():.4f}")
    print(f"Total cost: ${get_total_cost():.4f}")
