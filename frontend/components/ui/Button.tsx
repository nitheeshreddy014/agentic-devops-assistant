'use client';
import { forwardRef, ButtonHTMLAttributes } from 'react';

const variants = {
  primary:   'bg-blue-600 hover:bg-blue-500 text-white border-transparent',
  secondary: 'bg-gray-700 hover:bg-gray-600 text-white border-transparent',
  danger:    'bg-red-700   hover:bg-red-600   text-white border-transparent',
  ghost:     'bg-transparent hover:bg-gray-800 text-gray-300 border-gray-600',
};
const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2   text-sm',
  lg: 'px-6 py-3   text-base',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:   keyof typeof variants;
  size?:      keyof typeof sizes;
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', isLoading, children, className = '', disabled, ...rest }, ref) => (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium border
        transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${className}`}
      {...rest}
    >
      {isLoading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      )}
      {children}
    </button>
  )
);
Button.displayName = 'Button';
