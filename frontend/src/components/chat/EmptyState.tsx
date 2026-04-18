/**
 * EmptyState — premium dark landing view when no conversation is active.
 *
 * Features:
 * - Large clean greeting heading
 * - 4 horizontal suggestion cards with icons
 * - Minimal, ultra-dark aesthetic
 */

import { motion } from "framer-motion";
import {
  IconBarChart,
  IconTrendingUp,
  IconMessageSquare,
  IconPackage,
} from "../ui/icons";

interface EmptyStateProps {
  onSelectQuestion: (question: string) => void;
}

const SUGGESTIONS = [
  {
    text: "Compare top 5 marketing campaigns by revenue",
    icon: IconBarChart,
  },
  {
    text: "What are customers saying about packaging?",
    icon: IconMessageSquare,
  },
  {
    text: "Show freight cost breakdown by warehouse",
    icon: IconPackage,
  },
  {
    text: "Why did profit margins drop last quarter?",
    icon: IconTrendingUp,
  },
] as const;

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (idx: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.45,
      delay: 0.35 + idx * 0.1,
      ease: "easeOut",
    },
  }),
};

export function EmptyState({
  onSelectQuestion,
}: EmptyStateProps): React.ReactElement {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Subtle ambient glow */}
      <div
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] rounded-full pointer-events-none"
        style={{
          background: "radial-gradient(ellipse, rgba(99,102,241,0.04) 0%, transparent 70%)",
        }}
      />

      <div className="max-w-3xl w-full relative z-10">
        {/* Greeting */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-4"
        >
          <h1 className="text-4xl md:text-5xl font-semibold tracking-tight leading-[1.1] bg-gradient-to-b from-[#FFFFFF] to-[#A3A3A3] text-transparent bg-clip-text pb-2">
            Hi there, Ui Mahadi<br />
            What would you like to know?
          </h1>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-sm text-[#A3A3A3] mb-10"
        >
          Use one of the prompts below or ask your own question to begin
        </motion.p>

        {/* Suggestion cards — horizontal row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {SUGGESTIONS.map((q, idx) => {
            const Icon = q.icon;
            return (
              <motion.button
                key={idx}
                custom={idx}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                whileHover={{
                  y: -3,
                  borderColor: "rgba(99,102,241,0.3)",
                  transition: { duration: 0.2 },
                }}
                whileTap={{ scale: 0.97 }}
                onClick={() => onSelectQuestion(q.text)}
                className="
                  text-left p-4 rounded-xl
                  border border-[#333333] bg-[#212121]
                  hover:brightness-110
                  transition-all duration-300
                  focus-ring group cursor-pointer
                  flex flex-col justify-between
                  min-h-[120px]
                "
              >
                <span className="text-[13px] text-[#A3A3A3] group-hover:text-white transition-colors leading-relaxed">
                  {q.text}
                </span>
                <div className="mt-3">
                  <Icon
                    size={18}
                    className="text-text-muted group-hover:text-text-secondary transition-colors"
                  />
                </div>
              </motion.button>
            );
          })}
        </div>

        {/* Footer */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.9 }}
          className="text-center text-xs text-[#A3A3A3] mt-12 tracking-wide"
        >
          Powered by RAG + SQL analytics • Charts generated automatically
        </motion.p>
      </div>
    </div>
  );
}
