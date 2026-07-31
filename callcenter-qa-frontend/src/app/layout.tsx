import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "QA звонков",
  description: "Локальная платформа анализа качества звонков",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
