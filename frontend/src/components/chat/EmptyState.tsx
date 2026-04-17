/**
 * EmptyState — premium landing view when no conversation is active.
 *
 * Features:
 * - Animated gradient orbs background
 * - Gradient text heading
 * - Icon-enriched question cards with staggered animations
 * - Responsive grid (3-col desktop, 2 tablet, 1 mobile)
 */

import { motion } from "framer-motion";
import {
  IconBarChart,
  IconTrendingUp,
  IconMessageSquare,
  IconPackage,
  IconGlobe,
  IconTarget,
} from "../ui/icons";

interface EmptyStateProps {
  onSelectQuestion: (question: string) => void;
}

const EXAMPLE_QUESTIONS = [
  {
    text: "Why did net profit margin drop last month?",
    icon: IconTrendingUp,
    gradient: "from-red-500/20 to-orange-500/20",
    iconColor: "text-red-400",
  },
  {
    text: "Which campaigns have the best ROI?",
    icon: IconTarget,
    gradient: "from-indigo-500/20 to-purple-500/20",
    iconColor: "text-indigo-400",
  },
  {
    text: "What are customers saying about packaging?",
    icon: IconMessageSquare,
    gradient: "from-emerald-500/20 to-teal-500/20",
    iconColor: "text-emerald-400",
  },
  {
    text: "Compare freight costs across warehouses",
    icon: IconPackage,
    gradient: "from-amber-500/20 to-yellow-500/20",
    iconColor: "text-amber-400",
  },
  {
    text: "How does our return rate compare to industry?",
    icon: IconGlobe,
    gradient: "from-cyan-500/20 to-blue-500/20",
    iconColor: "text-cyan-400",
  },
  {
    text: "Show revenue breakdown by campaign channel",
    icon: IconBarChart,
    gradient: "from-pink-500/20 to-rose-500/20",
    iconColor: "text-pink-400",
  },
] as const;

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: (idx: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      delay: 0.2 + idx * 0.08,
      ease: "easeOut",
    },
  }),
};

export function EmptyState({
  onSelectQuestion,
}: EmptyStateProps): React.ReactElement {
  return (
    <div className="flex-1 flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background orbs */}
      <div className="orb w-[300px] h-[300px] bg-indigo-500 -top-20 -right-20" />
      <div
        className="orb w-[250px] h-[250px] bg-purple-500 bottom-10 -left-16"
        style={{ animationDelay: "4s" }}
      />
      <div
        className="orb w-[200px] h-[200px] bg-pink-500 top-1/3 right-1/4"
        style={{ animationDelay: "8s" }}
      />

      <div className="max-w-3xl w-full relative z-10">
        {/* Heading */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 mb-6 rounded-full border border-accent/20 bg-accent/5"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span className="text-xs font-semibold text-accent tracking-widest uppercase">
              Intelligence Agent
            </span>
          </motion.div>

          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-4 tracking-tight">
            What would you like to{" "}
            <span className="gradient-text">analyse</span>?
          </h1>
          <p className="text-base md:text-lg text-text-secondary max-w-lg mx-auto">
            Ask anything about revenue, campaigns, customer feedback, or market trends
          </p>
        </motion.div>

        {/* Question grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {EXAMPLE_QUESTIONS.map((q, idx) => {
            const Icon = q.icon;
            return (
              <motion.button
                key={idx}
                custom={idx}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                whileHover={{ y: -2, transition: { duration: 0.2 } }}
                whileTap={{ scale: 0.98 }}
                onClick={() => onSelectQuestion(q.text)}
                className={`
                  text-left p-4 rounded-xl
                  border border-border bg-bg-surface/80
                  hover:border-accent/30 hover:shadow-glow
                  transition-all duration-300
                  focus-ring group cursor-pointer
                  backdrop-blur-sm
                `}
              >
                <div
                  className={`
                    w-9 h-9 rounded-lg flex items-center justify-center mb-3
                    bg-gradient-to-br ${q.gradient}
                    group-hover:scale-110 transition-transform duration-300
                  `}
                >
                  <Icon size={18} className={q.iconColor} />
                </div>
                <span className="text-sm text-text-secondary group-hover:text-text-primary transition-colors leading-relaxed">
                  {q.text}
                </span>
              </motion.button>
            );
          })}
        </div>

        {/* Subtle footer hint */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.8 }}
          className="text-center text-xs text-text-muted mt-10"
        >
          Powered by RAG + SQL analytics • Charts generated automatically
        </motion.p>
      </div>
    </div>
  );
}
