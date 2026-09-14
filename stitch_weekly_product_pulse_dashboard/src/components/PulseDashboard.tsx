"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Share } from "./Share";
import { BarChart3, RefreshCw } from "lucide-react";
import { runAnalysis } from "@/app/actions";
import ReactMarkdown from "react-markdown";

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
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-12">
        <div className="flex items-center space-x-3">
          <div className="bg-[#24a485] text-white w-8 h-8 rounded flex items-center justify-center font-bold text-sm">
            GW
          </div>
          <span className="font-bold text-gray-900">Groww</span>
        </div>
        <div className="text-gray-500 text-sm font-medium">Product Pulse</div>
      </div>

      {/* Controls */}
      <div className="flex items-center space-x-4 mb-16">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          Period
        </div>
        <select
          className="bg-white border border-gray-200 rounded-full px-4 py-2 text-sm font-medium text-gray-700 outline-none hover:bg-gray-50 cursor-pointer"
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
          className="flex items-center space-x-2 bg-white border border-gray-200 rounded-full px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw
            size={14}
            className={`text-[#b86b52] ${isRefreshing ? "animate-spin" : ""}`}
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
        {reviewCount > 0 && (
          <span className="text-xs text-gray-500">
            ({reviewCount} reviews analyzed)
          </span>
        )}
        {isRefreshing ? (
          <span className="bg-[#fff4e5] text-[#b06000] text-xs font-bold px-2.5 py-1 rounded-full">
            ANALYZING…
          </span>
        ) : (
          <span className="bg-[#e6f4ea] text-[#137333] text-xs font-bold px-2.5 py-1 rounded-full">
            REPORT READY
          </span>
        )}
      </div>

      {/* Main Report Card */}
      <div className="bg-white rounded-[2rem] p-10 md:p-14 shadow-sm">
        <div className="flex items-center space-x-3 mb-2">
          <BarChart3 className="text-[#b86b52]" size={32} />
          <h1 className="font-serif text-3xl md:text-4xl text-gray-900 font-bold italic">
            Weekly Product Pulse — Groww
          </h1>
        </div>
        <div className="text-gray-500 text-sm mb-10">
          Past 7 Days | {dateRange}
        </div>

        {/* Pulse Markdown Body */}
        <div className="prose prose-gray max-w-none pulse-body">
          <ReactMarkdown
            components={{
              // Style headings and paragraphs to match the existing design
              p: ({ children }) => (
                <p className="text-gray-700 leading-relaxed mb-4">{children}</p>
              ),
              strong: ({ children }) => (
                <strong className="font-bold text-gray-900">{children}</strong>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside space-y-2 mb-4 text-gray-700">
                  {children}
                </ol>
              ),
              ul: ({ children }) => (
                <ul className="list-disc list-inside space-y-2 mb-4 text-gray-700">
                  {children}
                </ul>
              ),
              li: ({ children }) => (
                <li className="leading-relaxed">{children}</li>
              ),
              hr: () => <hr className="my-6 border-gray-100" />,
            }}
          >
            {pulseBody}
          </ReactMarkdown>
        </div>

        {/* Share Component */}
        <Share />
      </div>
    </div>
  );
}
