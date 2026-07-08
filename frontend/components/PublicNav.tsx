import Image from "next/image";
import Link from "next/link";

const PublicNav = () => {
  return (
    <nav className="bg-card border-b border-border px-6 py-4">
      <Link href="/" className="inline-flex items-center gap-2 w-fit">
        <Image
          src="/images/logo-light.png"
          alt="Zinmac"
          width={32}
          height={32}
          className="w-8 h-8 dark:hidden"
        />
        <Image
          src="/images/logo-dark.png"
          alt="Zinmac"
          width={32}
          height={32}
          className="w-8 h-8 hidden dark:block"
        />
        <span className="font-serif text-[19px] text-text">Zinmac</span>
      </Link>
    </nav>
  );
};

export default PublicNav;
