"use client"

import { useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
    }
  }, [router]);

  return (
    <div className="flex h-screen w-full">
      <Suspense fallback={<div className="w-64 bg-sidebar" />}>
        <Sidebar />
      </Suspense>
      <main className="flex-1 flex flex-col overflow-y-auto overflow-x-hidden bg-muted/30 relative scroll-smooth">
        {children}
      </main>
    </div>
  );
}
