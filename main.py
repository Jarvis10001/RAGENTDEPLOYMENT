"""E-commerce Intelligence Agent — main entry point.

Usage
-----
    # Launch the Streamlit chat UI (recommended)
    streamlit run ui/streamlit_app.py

    # Quick smoke-test: verify config loads and agent builds
    python main.py
"""

from __future__ import annotations

import sys


def main() -> None:
    """Verify configuration and print startup summary."""
    try:
        from src.config import settings

        print("✅ Config loaded")
        print(f"   Primary model  : {settings.primary_model}")
        print(f"   Sub-agent model: {settings.sub_agent_model}")
        print(f"   Supabase URL   : {settings.supabase_url}")
        print(f"   Cache enabled  : {settings.cache_enabled}")
        print(f"   Debug          : {settings.debug}")
        print()
        print("To start the UI, run:")
        print("   streamlit run ui/streamlit_app.py")

    except Exception as exc:
        print(f"❌ Startup failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
