import React from "react";

export const FloatingParticles: React.FC = () => {
  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden z-0"
      aria-hidden="true"
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(79,70,229,0.02),transparent_50%)] animate-pulse" />
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-500/5 rounded-full blur-[120px] animate-float opacity-50" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-emerald-500/5 rounded-full blur-[120px] animate-float-delayed opacity-50" />
    </div>
  );
};
