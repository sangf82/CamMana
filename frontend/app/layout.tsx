import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "../components/layout/Sidebar";
import { Toaster } from "sonner";
import { ThemeProvider } from "../components/theme-provider";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "CamMana - Hệ thống giám sát",
  description: "Hệ thống quản lý và giám sát camera công nghiệp",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${mono.variable} font-sans antialiased bg-background text-foreground overflow-hidden`}
        suppressHydrationWarning
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <div className="flex h-screen w-full">
            <Sidebar />
            <main className="flex-1 flex flex-col overflow-hidden bg-muted/30 relative">
              {children}
            </main>
          </div>
          <Toaster position="top-right" richColors closeButton theme="dark" />
        </ThemeProvider>
      </body>
    </html>
  );
}
