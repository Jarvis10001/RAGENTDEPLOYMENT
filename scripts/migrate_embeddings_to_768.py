"""
Migrate embeddings from 384-dim to 768-dim using Google Gemini Embedding API.

Reads CSV files, generates 768-dimensional embeddings locally,
and overwrites existing data in Supabase.

Usage:
    python scripts/migrate_embeddings_to_768.py
"""

import pandas as pd
import sys
import time
from pathlib import Path
import google.generativeai as genai

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.db.supabase_client import get_supabase_client

def get_google_embeddings_client():
    """Initialize Google Generative AI client for embeddings."""
    print("Initializing Google Generative AI client...")
    genai.configure(api_key=settings.google_api_key)
    print("✅ Google client initialized!")
    return genai

def get_embedding(text: str) -> list[float] | None:
    """Generate embedding using Google's API.
    
    Args:
        text: Text to embed.
        
    Returns:
        Embedding vector as list of floats, or None if text is empty.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    
    try:
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            output_dimensionality=768,
        )
        return response["embedding"]
    except Exception as e:
        print(f"  ✗ Embedding error: {e}")
        return None


def migrate_omnichannel(csv_file: str, start_row: int = 0):
    """Migrate omnichannel embeddings using Google API.
    
    Args:
        csv_file: Path to omnichannel_feedback.csv
        start_row: Row index to start from (useful for resuming after rate limits).
    """
    print(f"\n🔄 MIGRATING OMNICHANNEL VECTORS")
    print(f"Reading: {csv_file}")
    
    try:
        df = pd.read_csv(csv_file)
        print(f"Found {len(df)} rows to process")
        
        supabase = get_supabase_client()
        
        for i, row in df.iterrows():
            if i < start_row:
                continue
                
            text = row.get('text_content', '')
            embedding = get_embedding(text)
            
            if embedding:
                try:
                    # Delete old record if it exists
                    if pd.notna(row.get('feedback_id')):
                        supabase.table("omnichannel_vectors").delete().eq(
                            "feedback_id", str(row['feedback_id'])
                        ).execute()
                    
                    # Insert new record with 768-dim embedding
                    record = {
                        "feedback_id": row.get('feedback_id'),
                        "order_id": row.get('order_id'),
                        "text_content": text,
                        "embedding": embedding,
                    }
                    supabase.table("omnichannel_vectors").insert(record).execute()
                    
                    if (i + 1) % 10 == 0:
                        print(f"  ✓ {i + 1}/{len(df)} rows migrated")
                        time.sleep(2.5)  # Increased rate limiting to play it safe with Google Free API
                        
                except Exception as e:
                    print(f"  ✗ Error on row {i}: {e}")
                    
        print(f"✅ Omnichannel migration complete! ({len(df)} rows)")
        
    except FileNotFoundError:
        print(f"❌ File not found: {csv_file}")
    except Exception as e:
        print(f"❌ Migration error: {e}")


def migrate_marketing(csv_file: str, start_row: int = 0):
    """Migrate marketing embeddings using Google API.
    
    Args:
        csv_file: Path to marketing_assets_and_briefs.csv
        start_row: Row index to start from (useful for resuming after rate limits).
    """
    print(f"\n🔄 MIGRATING MARKETING VECTORS")
    print(f"Reading: {csv_file}")
    
    try:
        df = pd.read_csv(csv_file)
        print(f"Found {len(df)} rows to process")
        
        supabase = get_supabase_client()
        
        for i, row in df.iterrows():
            if i < start_row:
                continue
                
            text = row.get('text_content', '')
            embedding = get_embedding(text)
            
            if embedding:
                try:
                    # Delete old record if it exists
                    if pd.notna(row.get('asset_id')):
                        supabase.table("marketing_vectors").delete().eq(
                            "asset_id", str(row['asset_id'])
                        ).execute()
                    
                    # Insert new record with 768-dim embedding
                    record = {
                        "asset_id": row.get('asset_id'),
                        "campaign_id": row.get('campaign_id'),
                        "asset_type": row.get('asset_type'),
                        "text_content": text,
                        "embedding": embedding,
                    }
                    supabase.table("marketing_vectors").insert(record).execute()
                    
                    if (i + 1) % 10 == 0:
                        print(f"  ✓ {i + 1}/{len(df)} rows migrated")
                        time.sleep(2.5)  # Increased rate limiting to play it safe with Google Free API
                        
                except Exception as e:
                    print(f"  ✗ Error on row {i}: {e}")
                    
        print(f"✅ Marketing migration complete! ({len(df)} rows)")
        
    except FileNotFoundError:
        print(f"❌ File not found: {csv_file}")
    except Exception as e:
        print(f"❌ Migration error: {e}")


def main():
    """Entry point."""
    print("=" * 60)
    print("EMBEDDING MIGRATION: 384-dim → 768-dim (Google API)")
    print("=" * 60)
    
    # Initialize Google client
    get_google_embeddings_client()
    
    # CSV file paths
    omnichannel_csv = r"e:\RAGENT2\Default (1)\omnichannel_feedback.csv"
    marketing_csv = r"e:\RAGENT2\Default (1)\marketing_assets_and_briefs.csv"
    
    # Migrate both tables
    # migrate_omnichannel(omnichannel_csv, start_row=930)
    migrate_marketing(marketing_csv, start_row=0)
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("All embeddings are now 768-dimensional (Google Embedding API)")
    print("=" * 60)


if __name__ == "__main__":
    main()
