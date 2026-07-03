import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import ThemeProvider from "@/components/ThemeProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Zinmac | 한의사 전용 AI 진단 보조",
  description:
    "한의사 전용 AI 진단 보조 서비스. 음성 녹음으로 자동 차팅, 사상체질 판별, 한약 처방 추천.",
  keywords:
    "한의사, AI 진단, 오토차팅, 사상체질, 한약 처방, 침 처방, 한의원, 환자관리",
  manifest: "/manifest.json",
  openGraph: {
    title: "Zinmac | 한의사 전용 AI 진단 보조",
    description: "음성 녹음으로 자동 차팅, 사상체질 판별, 한약 처방 추천.",
    locale: "ko_KR",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
 return (
    <html lang="ko" className="h-full antialiased" suppressHydrationWarning>

      <body className="min-h-full flex flex-col font-sans">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}