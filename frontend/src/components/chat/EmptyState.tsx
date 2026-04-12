/**
 * EmptyState — centered landing view when no conversation is active.
 *
 * Large heading, subtitle, and a 2-column grid of 6 example question cards.
 */

import { motion } from "framer-motion";

interface EmptyStateProps {
  onSelectQuestion: (question: string) => void;
}

const EXAMPLE_QUESTIONS = [
  "Why did net profit margin drop last month?",
  "Which campaigns have the best ROI?",
  "What are customers saying about packaging?",
  "Compare freight costs across warehouses",
  "How does our return rate compare to industry?",
  "Is our campaign messaging aligned with feedback?",
] as const;

export function EmptyState({
  onSelectQuestion,
}: EmptyStateProps): React.ReactElement {
  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="max-w-2xl w-full">
        {/* Heading */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-center mb-10"
        >
          <div className="flex justify-center items-center gap-2 mb-4">
            <span className="px-3 py-1 bg-accent/10 border border-accent/20 rounded-full text-xs font-bold text-accent tracking-widest uppercase">
              E-Commerce Intelligence Agent
            </span>
          </div>
          <h1 className="text-3xl font-semibold text-text-primary mb-3">
            What would you like to analyse?
          </h1>
          <p className="text-base text-text-secondary">
            Ask anything about revenue, campaigns, or customer feedback
          </p>
        </motion.div>

        {/* Question grid */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="grid grid-cols-1 sm:grid-cols-2 gap-3"
        >
          {EXAMPLE_QUESTIONS.map((question, idx) => (
            <button
              key={idx}
              onClick={() => onSelectQuestion(question)}
              className="
                text-left p-4 rounded-card
                border border-border bg-bg-surface
                hover:border-accent/40 hover:bg-bg-elevated
                transition-all duration-200
                focus-ring
                group
              "
            >
              <span className="text-sm text-text-secondary group-hover:text-text-primary transition-colors">
                {question}
              </span>
            </button>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
