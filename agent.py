import os
import json
import requests
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "score_research",
            "description": "Score research coverage 1-10. Call after gathering information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "description": "Coverage score 1-10"},
                    "reasoning": {"type": "string", "description": "Why this score and what gaps remain"},
                    "needs_more_research": {"type": "boolean", "description": "True if score < 7"}
                },
                "required": ["score", "reasoning", "needs_more_research"]
            }
        }
    }
]

def call_mistral(messages):
    resp = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "mistral-small-latest",
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto"
        },
        timeout=60
    )
    if not resp.ok:
        raise Exception(f"Mistral error {resp.status_code}: {resp.text}")
    return resp.json()

def run_tool(name, args):
    if name == "web_search":
        results = tavily.search(query=args["query"], max_results=5)
        formatted = []
        for r in results.get("results", []):
            formatted.append(f"Title: {r['title']}\nSummary: {r['content']}\nSource: {r['url']}")
        return "\n---\n".join(formatted)
    elif name == "score_research":
        return json.dumps(args)
    return "Tool not found"


def run_agent(topic: str, on_update=None):
    def emit(stage, message):
        if on_update:
            on_update(stage, message)

    emit("planner", f"Breaking down research topic: **{topic}**")

    messages = [
        {
            "role": "system",
            "content": """You are an autonomous research agent. When given a topic:
1. Use web_search 3-5 times with different queries to gather info from multiple angles
2. Use score_research to evaluate coverage (score 1-10)
3. If score < 7, search more to fill gaps
4. Once score >= 7, write a full research report in markdown with:
   - Introduction
   - 3-5 sections on different aspects
   - Real facts and data from searches
   - Citations section with all source URLs"""
        },
        {
            "role": "user",
            "content": f"Research this topic thoroughly and write a cited report: {topic}"
        }
    ]

    all_sources = []
    loop_count = 0
    max_loops = 15

    while loop_count < max_loops:
        loop_count += 1

        data = call_mistral(messages)
        choice = data["choices"][0]
        msg = choice["message"]
        finish_reason = choice["finish_reason"]
        tool_calls = msg.get("tool_calls") or []

        messages.append(msg)

        if finish_reason == "stop" or not tool_calls:
            emit("writer", "Writing final report...")
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
            return content or "No report generated.", all_sources

        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except Exception:
                args = {}

            if name == "web_search":
                emit("search", f"Searching: *{args.get('query', '')}*")
                result = run_tool(name, args)
                for line in result.split("\n"):
                    if line.startswith("Source: "):
                        url = line.replace("Source: ", "").strip()
                        if url not in all_sources:
                            all_sources.append(url)

            elif name == "score_research":
                score = args.get("score", 0)
                reasoning = args.get("reasoning", "")
                needs_more = args.get("needs_more_research", False)
                emit("critic", f"Coverage score: **{score}/10** — {reasoning}")
                if not needs_more:
                    emit("writer", "Research complete. Writing report...")
                result = run_tool(name, args)
            else:
                result = "Tool not found"

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result
            })

    return "Research loop ended without a final report.", all_sources