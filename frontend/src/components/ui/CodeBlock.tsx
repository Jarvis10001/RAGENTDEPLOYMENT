/**
 * CodeBlock — custom renderer for fenced code blocks in markdown.
 * Dark surface, monospace font, copy button (text "Copy"/"Copied").
 */

import { useState, useCallback } from "react";

interface CodeBlockProps {
  children: string;
  language?: string;
}

export function CodeBlock({ children, language }: CodeBlockProps): React.ReactElement {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(children).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [children]);

  return (
    <div className="relative group my-3 rounded-card overflow-hidden border border-border">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-bg-elevated border-b border-border">
        <span className="text-2xs font-medium text-text-muted uppercase tracking-wider">
          {language || "code"}
        </span>
        <button
          onClick={handleCopy}
          className="
            text-2xs font-medium px-2 py-0.5 rounded-input
            text-text-muted hover:text-text-primary
            transition-colors focus-ring
          "
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {/* Code content */}
      <div className="overflow-x-auto bg-bg-surface">
        <pre className="p-4 text-sm leading-relaxed">
          <code className="font-mono text-text-primary whitespace-pre">
            {children}
          </code>
        </pre>
      </div>
    </div>
  );
}
