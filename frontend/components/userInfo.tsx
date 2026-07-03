import { useEffect, useState } from "react";
import { getMe } from '@/lib/api/get-me';
import DotSpinner from "./spinner";
import { MembershipBadge } from "./MembershipBadge";

type User = {
  expired_at: string | null;
  hospital_id: string;
  id: string;
  institution_code: string;
  license_number: string;
  name: string;
  role: "owner" | "staff";
  tier: "basic" | "premium";
};

export const UserInfoForNav = () => {
  const [me, setMe] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe().then((myData: any) => {
      if (myData) setMe(myData);
      setLoading(false);
    });
  }, []);
// useEffect 아래에 임시로 추가 (개발 중에만 사용)
// useEffect(() => {
//   // getMe() 호출 대신 테스트 데이터 사용
//   const testData: User = {
//     expired_at: "2026-07-09",        // ← 오늘로부터 약 5일 후 (현재 날짜 기준)
//     // expired_at: null,             // 만료 테스트
//     hospital_id: "test",
//     id: "test",
//     institution_code: "test",
//     license_number: "test",
//     name: "테스트 사용자",
//     role: "owner",
//     tier: "premium"
//   };
  
//   setMe(testData);
//   setLoading(false);
// }, []);

  if (loading || !me) return <DotSpinner />;

  const isExpired = !me.expired_at;
  

  const getDaysRemaining = (): number | null => {
    if (!me.expired_at) return null;
    const expiredDate = new Date(me.expired_at);
    const today = new Date();
    const diffTime = expiredDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 3600 * 24));
    return diffDays;
  };

  const daysRemaining = getDaysRemaining();
  const isExpiringSoon = daysRemaining !== null && daysRemaining <= 7 && daysRemaining > 0;
  const shouldHighlight = isExpired || isExpiringSoon;

  return (
    <div className="flex items-center gap-3 bg-zinc-800 hover:bg-zinc-700 transition-colors border border-zinc-700 rounded-xl px-4 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-medium text-white">{me.name}</span>
        <MembershipBadge tier={me.tier} />
      </div>


      <div className="w-px h-5 bg-zinc-600" />


      <div 
        className={`
          text-xs transition-all duration-300
          ${shouldHighlight 
            ? "text-red-400 animate-pulse font-medium" 
            : "text-zinc-400"
          }
        `}
      >
        {isExpired ? (
          <span className="flex items-center gap-1">결제 필요</span>
        ) : me.expired_at ? (   
          <span>
     
            {new Date(me.expired_at).toLocaleDateString('ko-KR', {
              month: 'short',
              day: 'numeric',
            })}
            {daysRemaining !== null && daysRemaining <= 7 && ` (${daysRemaining}일 남음)`}
          </span>
        ) : (
          "정보 없음"
        )}
      </div>
    </div>
  );
};