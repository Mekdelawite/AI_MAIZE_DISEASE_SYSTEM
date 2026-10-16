import React from 'react';

export const MaizeLogo: React.FC<{ className?: string }> = ({ className = 'w-6 h-6' }) => {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="8" className="fill-emerald-900 dark:fill-emerald-800" />
      <path
        d="M16 6C12.5 9.5 11 14 11 19.5C11 22.8 13.2 25.5 16 26C18.8 25.5 21 22.8 21 19.5C21 14 19.5 9.5 16 6Z"
        className="fill-amber-400"
      />
      <path
        d="M16 26C11.5 25.5 7.5 22 6.5 16.5C10.5 17 14 19.5 16 24.5"
        className="stroke-emerald-300"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M16 26C20.5 25.5 24.5 22 25.5 16.5C21.5 17 18 19.5 16 24.5"
        className="stroke-emerald-300"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M14.5 13H17.5M14 16.5H18M14.5 20H17.5"
        className="stroke-emerald-950"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
};
