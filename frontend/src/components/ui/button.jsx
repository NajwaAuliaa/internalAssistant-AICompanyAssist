import React from 'react';

const Button = React.forwardRef(({ className = "", variant = "default", size = "default", ...props }, ref) => {
  const variants = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90 border border-transparent",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-transparent",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    ghost: "hover:bg-accent hover:text-accent-foreground bg-transparent border-transparent",
    destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90 border border-transparent",
    link: "text-primary underline-offset-4 hover:underline h-auto p-0",
    // Sidebar specific variants
    "sidebar-ghost": "hover:bg-sidebar-accent text-sidebar-foreground hover:text-sidebar-accent-foreground bg-transparent border-transparent",
    "sidebar-default": "bg-sidebar-accent text-sidebar-accent-foreground hover:bg-sidebar-accent/80 border border-transparent",
  };

  const sizes = {
    default: "h-10 px-4 py-2",
    sm: "h-9 rounded-md px-3",
    lg: "h-11 rounded-md px-8",
    icon: "h-10 w-10",
  };

  return (
    <button
      className={`inline-flex items-center justify-center rounded-md text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 disabled:pointer-events-none disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
      ref={ref}
      {...props}
    />
  );
});

Button.displayName = "Button";

export { Button };