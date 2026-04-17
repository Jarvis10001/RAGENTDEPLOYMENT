/**
 * SourceCitations — list of URLs from web search results with icons.
 */

import { useStore } from "../../store/useStore";
import { IconExternalLink, IconGlobe } from "../ui/icons";

export function SourceCitations(): React.ReactElement {
  const citations = useStore((s) => s.sourceCitations);

  if (citations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-60 text-center px-4">
        <div className="w-12 h-12 rounded-xl bg-bg-elevated flex items-center justify-center mb-3">
          <IconGlobe size={20} className="text-text-muted" />
        </div>
        <p className="text-sm text-text-muted">No sources cited</p>
        <p className="text-xs text-text-muted/60 mt-1.5 max-w-[220px]">
          Web search citations will be listed here
        </p>
      </div>
    );
  }

  return (
    <div className="p-3 space-y-1">
      {citations.map((citation, idx) => (
        <a
          key={idx}
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          className="
            flex items-start gap-2.5 py-2.5 px-3 rounded-lg
            text-text-primary hover:bg-accent/5
            transition-colors focus-ring group
          "
        >
          <IconExternalLink
            size={13}
            className="text-text-muted group-hover:text-accent transition-colors mt-0.5 flex-shrink-0"
          />
          <div className="min-w-0">
            <span className="text-sm font-medium group-hover:text-accent transition-colors line-clamp-1">
              {citation.title}
            </span>
            <span className="block text-2xs text-text-muted truncate mt-0.5">
              {citation.url}
            </span>
          </div>
        </a>
      ))}
    </div>
  );
}
