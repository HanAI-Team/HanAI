"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

// 환자 목록은 /home(접수 대시보드)에 통합됐다. 기존 링크/북마크 호환용 리다이렉트.
export default function PatientsRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/home");
  }, [router]);
  return null;
}
