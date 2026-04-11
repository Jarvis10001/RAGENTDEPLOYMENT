"""Tools package — five LangChain @tool functions for the E-commerce Intelligence Agent.

Available tools
---------------
* omnichannel_feedback_search  — RAG over customer feedback (pgvector)
* marketing_content_search     — RAG over campaign ad copy (pgvector)
* ecommerce_sql_query          — Row-level SQL lookups via Gemini-generated SELECT
* ecommerce_analytics_query    — Aggregation / trend SQL via Gemini-generated SELECT
* web_market_search            — Live web search via Tavily SDK
"""
