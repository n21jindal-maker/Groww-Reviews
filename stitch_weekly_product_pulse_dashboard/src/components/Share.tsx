"use client";

import { useState } from "react";

export function Share() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent">("idle");

  const handleShare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setStatus("sending");
    
    try {
      const response = await fetch('/api/share', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      
      if (!response.ok) {
        throw new Error('Failed to send');
      }

      setStatus("sent");
      setTimeout(() => setStatus("idle"), 3000);
      setEmail("");
    } catch (error) {
      console.error("Error sharing:", error);
      setStatus("idle");
      alert("Failed to send report. Check server logs.");
    }
  };

  return (
    <div className="mt-16 pt-8 border-t border-gray-200">
      <h2 className="font-serif text-2xl text-gray-900 mb-2 italic">Share</h2>
      <p className="text-gray-600 mb-6 text-sm">
        Deliver the full pulse by email — same rich formatting as on this page.
      </p>

      <form onSubmit={handleShare} className="bg-[#f7f5f0] rounded-xl p-6">
        <label
          htmlFor="email"
          className="block text-sm font-medium text-gray-900 mb-2"
        >
          Email addresses
        </label>
        <input
          type="email"
          id="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="name@company.com"
          className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 mb-6 text-gray-900 outline-none focus:border-[#24a485] focus:ring-1 focus:ring-[#24a485] transition-colors"
          required
        />
        <button
          type="submit"
          disabled={status === "sending"}
          className="bg-[#24a485] text-white px-6 py-2.5 rounded-full hover:bg-[#1c836a] transition-colors disabled:opacity-70 font-medium text-sm"
        >
          {status === "idle" && "Send report"}
          {status === "sending" && "Sending..."}
          {status === "sent" && "Sent!"}
        </button>
      </form>
    </div>
  );
}
