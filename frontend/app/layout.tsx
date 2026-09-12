import type { Metadata } from 'next';
import './globals.css';
// Uses system font stack — avoids SSL/proxy issues fetching Google Fonts

export const metadata: Metadata = {
  title: 'Agentic DevOps Troubleshooting Assistant',
  description: 'Multi-agent AI investigation powered by LangGraph, CrewAI, and Groq',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
