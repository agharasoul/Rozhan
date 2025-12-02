import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "192.168.1.102",
    "192.168.1.105",
    "10.246.240.90", 
    "10.201.31.90",
    "10.34.223.90",
    "localhost",
    "127.0.0.1",
    "athletes-cancelled-evidence-korean.trycloudflare.com",
  ],
};

export default nextConfig;
