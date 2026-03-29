from langchain_tavily import TavilySearch

from core.config import Settings

settings = Settings()

tavily_search = TavilySearch(
    max_results=5,
    tavily_api_key=settings.TAVILY_API_KEY,
)
tavily_search.metadata = {"requires_approval": False}