import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import ThemeProvider from "@/components/ThemeProvider";
import Footer from "@/components/Footer";
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
  title: "Zinmac | 한의사 전용 AI 진료 기록 보조",
  description:
    "한의사 전용 AI 진료 기록 보조 서비스. 음성 녹음으로 자동 차팅, 사상체질 분석 참고자료, 처방 참고자료 제공. 최종 진단·처방은 면허 한의사가 직접 판단합니다.",
  keywords:
    "한의사, AI 차팅, 오토차팅, 사상체질, 한약 처방 참고자료, 침 처방, 한의원, 환자관리, 진료기록 관리",
  manifest: "/manifest.json",
  openGraph: {
    title: "Zinmac | 한의사 전용 AI 진료 기록 보조",
    description: "음성 녹음으로 자동 차팅, 사상체질 분석 참고자료, 처방 참고자료 제공.",
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
        <ThemeProvider>
          <div className="flex flex-col flex-1">
            <div className="flex-1">{children}</div>
            <Footer />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}