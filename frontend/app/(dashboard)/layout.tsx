"use client";
import PwaInstallGuide from "@/components/PwaInstallGuide";
import ThemeToggle from "@/components/ThemeToggle";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) router.push("/login");
  }, []);

  const navLinks = [
    { label: "홈", path: "/home" },
    { label: "진료", path: "/diagnosis" },
    { label: "청구", path: "/billing" },
    { label: "설정", path: "/settings" },
  ];

  const mobileNavLinks = [
    { label: "홈", path: "/home" },
    { label: "진료", path: "/patients" },
    { label: "설정", path: "/settings" },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      {/* PC 네비바 */}
      <nav className="hidden sm:flex h-[52px] bg-[#232323] dark:bg-card dark:border-b dark:border-border items-center px-6 flex-shrink-0">
        <div className="flex items-center gap-2 mr-9">
            <Image
            src="/images/logo-light.png"
            alt="Zinmac"
            width={40}
            height={40}
            className="w-10 h-10 dark:hidden"
          />
          <Image
            src="/images/logo-dark.png"
            alt="Zinmac"
            width={40}
            height={40}
            className="w-10 h-10 hidden dark:block"
          />
          <div className="font-serif text-[19px] text-white">Zinmac</div>
        </div>
        <div className="flex gap-1 flex-1">
          {navLinks.map((link) => (
            <button
              key={link.path}
              onClick={() => router.push(link.path)}
              className={`px-4 py-1.5 text-xs rounded-md transition-all font-sans ${
                pathname === link.path
                  ? "text-white bg-white/[0.06]"
                  : "text-[#585753] hover:text-white"
              }`}
            >
              {link.label}
            </button>
          ))}
        </div>
        <ThemeToggle />
      </nav>

      {/* 모바일 헤더 */}
      <div className="sm:hidden flex h-[50px] bg-[#232323] dark:bg-card dark:border-b dark:border-border items-center px-4 justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <Image   src="/images/logo-light.png"
 alt="Zinmac" width={36} height={36} className="w-9 h-9 dark:hidden" />
          <Image   src="/images/logo-dark.png"
 alt="Zinmac" width={36} height={36} className="w-9 h-9 hidden dark:block" />
          <div className="font-serif text-[19px] text-white">Zinmac</div>
        </div>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex flex-col gap-1 p-1"
          >
            <span className="w-[18px] h-[1.5px] bg-white block rounded" />
            <span className="w-[18px] h-[1.5px] bg-white block rounded" />
            <span className="w-[18px] h-[1.5px] bg-white block rounded" />
          </button>
        </div>
      </div>

      {/* 드로어 오버레이 */}
      {drawerOpen && (
        <div
          className="fixed inset-0 bg-[#232323]/50 z-[100] sm:hidden"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* 드로어 */}
      <div
        className={`fixed top-0 bottom-0 left-0 w-[240px] bg-[#232323] dark:bg-card dark:border-r dark:border-border z-[101] flex flex-col transition-transform duration-300 sm:hidden ${drawerOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Image src="/logo.png" alt="Zinmac" width={32} height={32} className="w-8 h-8" />
            <div className="font-serif text-[18px] text-white">Zinmac</div>
          </div>
          <button
            onClick={() => setDrawerOpen(false)}
            className="text-[#585753] text-xl"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 py-3">
          {navLinks.map((link) => (
            <button
              key={link.path}
              onClick={() => {
                router.push(link.path);
                setDrawerOpen(false);
              }}
              className={`w-full px-5 py-3 text-sm text-left flex items-center gap-3 transition-all ${
                pathname === link.path
                  ? "text-white bg-white/[0.06]"
                  : "text-[#585753] hover:text-white"
              }`}
            >
              {link.label}
            </button>
          ))}
        </div>
        <div className="px-5 py-4 border-t border-white/5 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[#68413E] flex items-center justify-center text-xs font-medium text-white">
            이
          </div>
          <div>
            <div className="text-xs font-medium text-white">이○○ 한의사</div>
            <div className="text-[10px] text-[#585753]">보령 한의원</div>
          </div>
        </div>
      </div>

      <PwaInstallGuide />

      {/* 메인 콘텐츠 */}
      <main className="flex-1">{children}</main>

      {/* 모바일 하단 탭바 */}
      <nav className="sm:hidden border-t border-border bg-card py-2 pb-3">
        <div className="flex justify-around">
          {mobileNavLinks.map((link) => {
            const isActive =
              pathname === link.path ||
              (link.path === "/patients" && pathname === "/diagnosis");
            return (
              <button
                key={link.path}
                onClick={() => router.push(link.path)}
                className={`flex flex-col items-center gap-0.5 px-4 py-1 ${
                  isActive ? "text-[#EF6600]" : "text-muted"
                }`}
              >
                <span className="text-[10px]">{link.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
