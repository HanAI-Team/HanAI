export const MembershipBadge = ({ tier }: { tier: string }) => {
  const isPremium = tier.toLowerCase() === "premium";

  return (
    <span
      className={`
        px-2.5 py-0.5 text-[10px] font-bold rounded-md tracking-wider
        ${isPremium 
          ? "bg-amber-500 text-black" 
          : "bg-blue-600 text-white"
        }
      `}
    >
      {isPremium ? "PREMIUM" : "BASIC"}
    </span>
  );
};