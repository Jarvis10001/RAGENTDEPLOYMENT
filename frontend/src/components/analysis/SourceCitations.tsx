/**
 * SourceCitations — list of URLs from web search results.
 * Clean linked text, no icons.
 */

import { useStore } from "../../store/useStore";

export function SourceCitations(): React.ReactElement {
  const citations = useStore((s) => s.sourceCitations);

  if (citations.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-text-muted">
        No sources cited
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {citations.map((citation, idx) => (
        <a
          key={idx}
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          className="
            block py-1.5 px-2 rounded-input text-sm
            text-accent hover:text-accent-hover
            hover:bg-accent-muted transition-colors
            truncate focus-ring
          "
        >
          {citation.title}
          <span className="ml-2 text-2xs text-text-muted">
            {citation.url.length > 60
              ? citation.url.slice(0, 60) + "..."
              : citation.url}
          </span>
        </a>
      ))}
    </div>
  );
}
