"use server";

import { revalidatePath } from "next/cache";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function runAnalysis() {
  try {
    const res = await fetch(`${API_URL}/api/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Allow up to 10 minutes for analyze + generate to finish
      signal: AbortSignal.timeout(600_000),
    });

    const data = await res.json();

    if (!res.ok || !data.success) {
      console.error("Refresh API failed:", data);
      return { success: false, error: data.error ?? "Unknown error" };
    }

    // Revalidate the home page so it reflects the newly generated pulse
    revalidatePath("/");
    return { success: true };
  } catch (error: any) {
    console.error("runAnalysis fetch failed:", error);
    return { success: false, error: error.message ?? String(error) };
  }
}
