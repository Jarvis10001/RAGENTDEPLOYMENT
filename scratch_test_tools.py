import sys
import logging

logging.basicConfig(level=logging.DEBUG)

from src.config import settings
from src.tools.sql_tools import ecommerce_analytics_query
from src.tools.rag_tools import marketing_content_search

def test():
    print("Testing ecommerce_analytics_query...")
    try:
        res = ecommerce_analytics_query.invoke({
            "question": "Which campaigns have the best ROI?"
        })
        print(f"Success! Result: {res[:200]}")
    except Exception as e:
        print(f"Error in SQL tool: {type(e).__name__}: {e}")

    print("\n------------------------------\n")

    print("Testing marketing_content_search...")
    try:
        res = marketing_content_search.invoke({
            "query": "best marketing campaign 2025"
        })
        print(f"Success! Result: {res[:200]}")
    except Exception as e:
        print(f"Error in RAG tool: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test()
