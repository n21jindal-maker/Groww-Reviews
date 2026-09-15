"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Share } from "./Share";
import { RefreshCw } from "lucide-react";
import { runAnalysis } from "@/app/actions";

interface ParsedPulse {
  title: string;
  themes: { name: string; mentions: string; quote: string }[];
  actions: { title: string; desc: string }[];
}

function parseMarkdown(md: string): ParsedPulse {
  const result: ParsedPulse = { title: "", themes: [], actions: [] };

  // Parse Title: first line
  const titleMatch = md.match(/^(?:#\s*|📊\s*)([^\n]+)/);
  if (titleMatch) {
    result.title = titleMatch[1].trim();
  } else {
    result.title = "Weekly Product Pulse — Groww";
  }

  // Parse Themes
  const themesSection = md.match(/(?:###\s*)?🔍 (?:\*\*)?TOP THEMES(?:\*\*)?\n([\s\S]*?)(?=\n+(?:###\s*)?💬|\n+(?:###\s*)?🎯|$)/);
  let parsedThemes: { name: string; mentions: string }[] = [];
  if (themesSection) {
    const lines = themesSection[1].split('\n').filter(l => l.trim().length > 0);
    parsedThemes = lines.map(line => {
      // e.g. "1. Positive Feedback & Praise (137 mentions)"
      const match = line.match(/^\d+\.\s*(.+?)\s+\((.+?)\)/);
      if (match) {
        return { name: match[1].trim(), mentions: match[2].trim() };
      }
      // fallback
      const fallbackMatch = line.match(/^\d+\.\s*(.+)/);
      return { name: fallbackMatch ? fallbackMatch[1].trim() : line.trim(), mentions: "" };
    });
  }

  // Parse Quotes
  const quotesSection = md.match(/(?:###\s*)?💬 (?:\*\*)?WHAT USERS ARE SAYING(?:\*\*)?\n([\s\S]*?)(?=\n+(?:###\s*)?🎯|$)/);
  let parsedQuotes: string[] = [];
  if (quotesSection) {
    const lines = quotesSection[1].split('\n').filter(l => l.trim().length > 0);
    parsedQuotes = lines.map(line => {
      // • "very good service"
      return line.replace(/^•\s*/, '').replace(/^"|"$/g, '').trim();
    });
  }

  // Combine Themes and Quotes
  result.themes = parsedThemes.map((t, i) => ({
    name: t.name,
    mentions: t.mentions,
    quote: parsedQuotes[i] || ""
  }));

  // Parse Actions
  const actionsSection = md.match(/(?:###\s*)?🎯 (?:\*\*)?ACTION IDEAS(?:\*\*)?\n([\s\S]*?)(?=\n+---|\n+📅|$)/);
  if (actionsSection) {
    const lines = actionsSection[1].split('\n').filter(l => l.trim().length > 0);
    result.actions = lines.map(line => {
      // 1. **Performance Upgrade:** Upgrade server infrastructure...
      const match = line.match(/^\d+\.\s*\*\*(.*?)\*\*\s*(.*)/);
      if (match) {
        return { title: match[1].replace(/:$/, "").trim(), desc: match[2].trim() };
      }
      const fallbackMatch = line.match(/^\d+\.\s*(.*)/);
      return { title: "Action", desc: fallbackMatch ? fallbackMatch[1].trim() : line };
    });
  }

  return result;
}

export function PulseDashboard({
  pulseBody,
  dateRange = "Recent",
  reviewCount = 0,
  availableDates = [],
  selectedDateId = "",
}: {
  pulseBody: string;
  dateRange?: string;
  reviewCount?: number;
  availableDates?: { id: string; label: string }[];
  selectedDateId?: string;
}) {
  const router = useRouter();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const parsedPulse = useMemo(() => parseMarkdown(pulseBody), [pulseBody]);

  const handleDateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    router.push(`/?date=${e.target.value}`);
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const res = await runAnalysis();
      if (!res?.success) alert("Failed to refresh: " + res?.error);
      else router.refresh();
    } catch {
      alert("Error refreshing analysis");
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#faf9f6] text-gray-900 font-sans">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Top Header */}
        <div className="flex items-center justify-between mb-12">
          <div className="flex items-center space-x-3">
            <div className="bg-[#24a485] text-white w-8 h-8 rounded flex items-center justify-center font-bold text-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>
              </svg>
            </div>
            <span className="font-bold text-gray-900 text-lg">Groww</span>
          </div>
          <div className="text-gray-500 text-sm font-medium">Product Pulse</div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-4 mb-16">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            Period
          </div>
          <select
            className="bg-white border border-gray-200 rounded-full px-4 py-2 text-sm font-medium text-gray-700 outline-none hover:bg-gray-50 cursor-pointer shadow-sm"
            value={selectedDateId}
            onChange={handleDateChange}
          >
            {availableDates.length > 0 ? (
              availableDates.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))
            ) : (
              <option>{dateRange}</option>
            )}
          </select>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center space-x-2 bg-white border border-gray-200 rounded-full px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw
              size={14}
              className={`text-[#24a485] ${isRefreshing ? "animate-spin" : ""}`}
            />
            <span>{isRefreshing ? "Refreshing..." : "Refresh"}</span>
          </button>
        </div>

        {/* Status Bar */}
        <div className="flex items-center space-x-3 mb-6">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            Viewing
          </span>
          <span className="text-sm font-bold text-gray-900">{dateRange}</span>
          {isRefreshing ? (
            <span className="bg-[#fff4e5] text-[#b06000] text-[10px] font-bold px-2 py-0.5 rounded-sm">
              ANALYZING…
            </span>
          ) : (
            <span className="bg-[#e6f4ea] text-[#137333] text-[10px] font-bold px-2 py-0.5 rounded-sm">
              REPORT READY
            </span>
          )}
        </div>

        {/* Main Report Card */}
        <div className="bg-white rounded-[2rem] p-10 md:p-14 shadow-sm">
          {/* Title Section */}
          <div className="mb-12">
            <h1 className="font-serif text-3xl md:text-4xl text-gray-900 mb-2">
              📊 <span className="italic">{parsedPulse.title.replace("Groww Weekly Review Pulse — ", "WeeklyProductPulse — ")}</span>
            </h1>
            <div className="text-gray-500 text-sm ml-10">
              Week {new Date().getFullYear()}-W{Math.ceil(new Date().getDate() / 7)} | {dateRange}
            </div>
          </div>

          {/* Overview Section */}
          <div className="mb-10">
            <h2 className="font-serif text-2xl italic text-gray-900 mb-4 flex items-center gap-2">
              📈 Overview
            </h2>
            <p className="text-gray-700 leading-relaxed ml-8">
              Users are generally satisfied with the app, though some key themes and areas for improvement have been highlighted across the {reviewCount} reviews analyzed this week.
            </p>
          </div>

          {/* Top Themes Section */}
          {parsedPulse.themes.length > 0 && (
            <div className="mb-12">
              <h2 className="font-serif text-2xl italic text-gray-900 mb-6 flex items-center gap-2">
                🔍 Top Themes
              </h2>
              <div className="space-y-6 ml-8">
                {parsedPulse.themes.map((theme, idx) => (
                  <div key={idx} className="flex flex-col space-y-3">
                    <div className="bg-[#f7f5f0] rounded-xl p-5 border border-gray-100 flex items-center gap-4">
                      <div className="w-8 h-8 rounded-full bg-[#24a485] text-white flex items-center justify-center font-bold text-sm shrink-0">
                        {idx + 1}
                      </div>
                      <div className="flex flex-col">
                        <div className="font-bold text-gray-900">{theme.name}</div>
                        <div className="text-xs text-gray-500 mt-1 space-x-3">
                          <span className="font-medium text-gray-700">{theme.mentions}</span>
                        </div>
                      </div>
                    </div>
                    {theme.quote && (
                      <div className="bg-[#f7f5f0] border-l-2 border-[#b86b52] rounded-r-xl p-4 ml-4 italic text-gray-700 text-sm">
                        "{theme.quote}"
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Ideas Section */}
          {parsedPulse.actions.length > 0 && (
            <div className="mb-12">
              <h2 className="font-serif text-2xl italic text-gray-900 mb-6 flex items-center gap-2">
                💡 Action Ideas
              </h2>
              <div className="space-y-4 ml-8">
                {parsedPulse.actions.map((action, idx) => (
                  <div key={idx} className="bg-white rounded-xl p-5 border border-gray-200 flex gap-4">
                    <div className="font-bold text-[#24a485] shrink-0 mt-0.5">
                      {idx + 1}
                    </div>
                    <div className="text-sm text-gray-700 leading-relaxed">
                      <strong>[{action.title}]</strong> : {action.desc}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Share Component */}
          <Share />
        </div>
      </div>
    </div>
  );
}
