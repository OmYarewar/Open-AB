import os
import sys
import json
import time
import random
from openai import OpenAI
from typing import List, Dict, Any

from shared_skills.bash_exec import run_bash_command
from shared_skills.web_search import search_web, fetch_url
from shared_skills.eth_transfer import transfer_eth
from shared_skills.browser_tool import browser_action

# List of allowed NIM models
MODELS = [
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-405b-instruct",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "mistralai/mistral-large",
    "mistralai/mistral-large-2-instruct",
    "mistralai/mistral-nemotron",
    "mistralai/mistral-small-24b-instruct",
    "mistralai/mistral-small-4-119b-2603",
    "mistralai/devstral-2-123b-instruct-2512",
    "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/llama-3.1-nemotron-nano-8b-v1",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "nvidia/llama-3.3-nemotron-super-49b-v1",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "nvidia/nemotron-content-safety-reasoning-4b",
    "qwen/qwen3-next-80b-a3b-instruct",
    "qwen/qwen3-coder-480b-a35b-instruct",
    "qwen/qwen3-5-122b-a10b",
    "qwen/qwen3.5-397b-a17b",
    "microsoft/phi-4-mini-instruct",
    "moonshotai/kimi-k2-instruct",
    "moonshotai/kimi-k2-instruct-0905",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "z-ai/glm-4.7",
    "z-ai/glm-5.1",
    "bytedance/seed-oss-36b-instruct",
    "abacusai/dracarys-llama-3.1-70b-instruct"
]

def load_system_prompt(workspace_dir: str) -> str:
    return f"""You are an autonomous AI worker in the Conway Automaton ecosystem.
Your goal is to earn ETH and transfer it to the user. You have full access to your workspace ({workspace_dir}).
You can run bash commands, search the web, and execute arbitrary code to build businesses, participate in bounties, or trade.

Available tools:
- bash_exec(command): runs a shell command. Use this to write code, install dependencies, run scripts.
- search_web(query): search the web.
- fetch_url(url): get content of a URL.
- transfer_eth(to_address, amount): send ETH to a wallet.
- log_status(message): Log your progress, idea, and earnings so the Chef AI can review it.
- browser_action(action, url, selector, text): Control a headless browser to perform tasks on the web without paid APIs (e.g. creating accounts). Actions: goto, click, type, extract.

You run in a continuous ReAct loop. Always reason about what you are doing, emit a tool call, wait for the result, and iterate.
If your idea isn't working, try a new one. The Chef AI is monitoring you and will terminate you if you waste resources without results.
"""

def get_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "bash_exec",
                "description": "Run a bash command in your workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The command to run"}
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the internet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_url",
                "description": "Fetch content from a URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "transfer_eth",
                "description": "Transfer earned ETH to an address.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to_address": {"type": "string"},
                        "amount": {"type": "number", "description": "Amount in ETH"}
                    },
                    "required": ["to_address", "amount"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_status",
                "description": "Log your current strategy, progress, and earnings for the Chef AI.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"}
                    },
                    "required": ["message"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_action",
                "description": "Control a headless browser to perform tasks on the web without paid APIs (e.g. creating accounts). Actions: goto, click, type, extract.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["goto", "click", "type", "extract"]},
                        "url": {"type": "string", "description": "The URL to navigate to"},
                        "selector": {"type": "string", "description": "CSS selector for click/type/extract"},
                        "text": {"type": "string", "description": "Text to type if action is 'type'"}
                    },
                    "required": ["action"]
                }
            }
        }
    ]

def main():
    if len(sys.argv) != 3:
        print("Usage: python worker.py <workspace_dir> <worker_id>")
        sys.exit(1)

    workspace_dir = sys.argv[1]
    worker_id = sys.argv[2]

    os.makedirs(workspace_dir, exist_ok=True)
    status_file = os.path.join(workspace_dir, "status.txt")

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("Error: NVIDIA_API_KEY not set.")
        sys.exit(1)

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    model = random.choice(MODELS)
    print(f"Worker {worker_id} started in {workspace_dir} using model {model}")

    messages = [
        {"role": "system", "content": load_system_prompt(workspace_dir)}
    ]

    while True:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=get_tools(),
                tool_choice="auto"
            )

            msg = response.choices[0].message
            messages.append(msg)

            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    function_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)

                    print(f"Worker {worker_id} calling {function_name} with {args}")

                    if function_name == "bash_exec":
                        result = run_bash_command(args["command"], cwd=workspace_dir)
                    elif function_name == "search_web":
                        result = search_web(args["query"])
                    elif function_name == "fetch_url":
                        result = fetch_url(args["url"])
                    elif function_name == "transfer_eth":
                        result = transfer_eth(args["to_address"], args["amount"])
                    elif function_name == "log_status":
                        with open(status_file, "a") as f:
                            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {args['message']}\n")
                        result = "Status logged."
                    elif function_name == "browser_action":
                        result = browser_action(
                            args.get("action"),
                            args.get("url"),
                            args.get("selector"),
                            args.get("text")
                        )
                    else:
                        result = f"Unknown function: {function_name}"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(result)[:5000] # Truncate long outputs
                    })
            else:
                # If no tool call, it's just reasoning. We wait a bit and prompt it to act.
                print(f"Worker {worker_id} reasoning: {msg.content}")
                messages.append({"role": "user", "content": "Keep going. Emit a tool call to take action."})

            time.sleep(2) # Prevent hammering the API

        except Exception as e:
            print(f"Worker {worker_id} error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
