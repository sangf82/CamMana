"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";

export default function WelcomePage() {
  const [showSplash, setShowSplash] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Show splash for 2.5 seconds then redirect to login
    const timer = setTimeout(() => {
      setShowSplash(false);
      // Small delay for exit animation
      setTimeout(() => {
        router.push("/login");
      }, 500);
    }, 2500);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <AnimatePresence>
      {showSplash && (
        <motion.div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#09090b] overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Animated gradient highlights - moving around */}
          <motion.div
            className="absolute w-[70%] h-[70%] bg-gradient-to-br from-amber-500/40 via-orange-500/30 to-transparent blur-[50px] rounded-full"
            animate={{
              x: ["-20%", "10%", "-10%", "-20%"],
              y: ["-20%", "-10%", "10%", "-20%"],
            }}
            transition={{
              duration: 8,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={{ top: "-10%", left: "-10%" }}
          />
          <motion.div
            className="absolute w-[55%] h-[55%] bg-amber-400/35 blur-[70px] rounded-full"
            animate={{
              x: ["-30%", "0%", "-20%", "-30%"],
              y: ["-30%", "-20%", "0%", "-30%"],
            }}
            transition={{
              duration: 10,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.5,
            }}
            style={{ top: "-20%", left: "-20%" }}
          />
          
          {/* Secondary moving glow on bottom right */}
          <motion.div
            className="absolute w-[45%] h-[45%] bg-amber-500/25 blur-[80px] rounded-full"
            animate={{
              x: ["20%", "-10%", "10%", "20%"],
              y: ["20%", "10%", "-10%", "20%"],
            }}
            transition={{
              duration: 12,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 1,
            }}
            style={{ bottom: "-10%", right: "-10%" }}
          />
          
          {/* Subtle zinc glow */}
          <motion.div
            className="absolute w-[35%] h-[35%] bg-zinc-500/15 blur-[80px] rounded-full"
            animate={{
              x: ["10%", "-20%", "10%"],
              y: ["-10%", "20%", "-10%"],
            }}
            transition={{
              duration: 15,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={{ bottom: "20%", right: "10%" }}
          />
          
          {/* Grid Pattern Background - More visible */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff25_1px,transparent_1px),linear-gradient(to_bottom,#ffffff25_1px,transparent_1px)] bg-[size:48px_48px]" />
          
          {/* Radial fade overlay for grid - less fade */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,#09090b_80%)]" />

          {/* Logo/Icon Animation */}
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{
              type: "spring",
              stiffness: 260,
              damping: 20,
              delay: 0.2,
            }}
            className="mb-8"
          >
            <div className="relative w-32 h-32 rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 p-1 shadow-2xl shadow-amber-500/30">
              <div className="w-full h-full rounded-xl bg-zinc-900 flex items-center justify-center overflow-hidden">
                <Image
                  src="/favicon.ico"
                  alt="CamMana"
                  width={80}
                  height={80}
                  className="object-contain"
                  priority
                />
              </div>
            </div>
          </motion.div>

          {/* App Name Animation */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.6 }}
            className="text-5xl font-bold text-white mb-3"
          >
            <span className="text-amber-400">Cam</span>
            <span className="text-white">Mana</span>
          </motion.h1>

          {/* Tagline Animation */}
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.5 }}
            className="text-zinc-400 text-lg mb-12"
          >
            Hệ thống quản lý xe tải thông minh
          </motion.p>

          {/* Loading Indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2 }}
            className="flex flex-col items-center"
          >
            {/* Animated dots */}
            <div className="flex space-x-2">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-3 h-3 rounded-full bg-amber-400"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 1, 0.5],
                  }}
                  transition={{
                    duration: 1,
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                />
              ))}
            </div>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.5 }}
              className="text-zinc-500 text-sm mt-4"
            >
              Đang khởi động...
            </motion.p>
          </motion.div>

          {/* Bottom branding */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.8 }}
            className="absolute bottom-8 text-center"
          >
            <p className="text-zinc-600 text-xs">
              Camera Manager for Industrial Trucks
            </p>
            <p className="text-zinc-700 text-xs mt-1">
              v1.0.0
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
