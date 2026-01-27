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
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5 }}
        >
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
