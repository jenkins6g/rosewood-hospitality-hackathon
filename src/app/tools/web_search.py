import json
from urllib import error, request

from langchain_core.tools import tool

from src.app.config import Settings


def build_web_search(settings: Settings):
    @tool("web_search")
    def web_search(query: str) -> str:
        """Search the public web for current information and return compact results."""
        if not settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is not configured.")

        payload = json.dumps(
            {
                "query": query,
                "search_depth": "basic",
                "max_results": settings.web_search_max_results,
                "include_answer": True,
            }
        ).encode("utf-8")
        req = request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={
                "Authorization": f"Bearer {settings.tavily_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=settings.http_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Tavily search failed: {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise ValueError(f"Tavily search failed: {exc.reason}") from exc

        sections: list[str] = []
        answer = str(body.get("answer", "")).strip()
        if answer:
            sections.append(f"Answer: {answer}")

        results = body.get("results", []) or []
        if not results:
            sections.append("No web results returned.")
        else:
            lines = []
            for result in results[: settings.web_search_max_results]:
                title = result.get("title", "(untitled)")
                url = result.get("url", "")
                content = str(result.get("content", "")).strip().replace("\n", " ")
                snippet = content[:240] + ("..." if len(content) > 240 else "")
                lines.append(f"- {title} | {url}\n  {snippet}")
            sections.append("Sources:\n" + "\n".join(lines))

        return "\n\n".join(sections)

    return web_search
