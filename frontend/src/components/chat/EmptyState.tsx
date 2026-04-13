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

        {/* Render Cold Start Notice */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-10 p-4 rounded-xl border border-blue-500/20 bg-blue-500/5 flex items-start sm:items-center gap-3 text-sm text-blue-400/90 shadow-sm"
        >
          <svg className="w-6 h-6 shrink-0 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-left">
            <strong>Heads up!</strong> Since the backend is hosted on Render's free tier, it spins down after a period of inactivity. <strong>Your first request might take up to 50 seconds</strong> to wake the server up, but it will run at normal blazing speeds right after that!
          </p>
        </motion.div>
      </div>
    </div>
  );
}
