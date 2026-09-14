import { PulseDashboard } from '@/components/PulseDashboard';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/** Parse the YAML front-matter block to strip it from the body for display. */
function parsePulseBody(content: string): string {
  const fmMatch = content.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n([\s\S]*)$/);
  return fmMatch ? fmMatch[1] : content;
}

type PulseMeta = {
  id: string;
  label: string;
  review_count: number;
  start_date?: string;
  end_date?: string;
};

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const resolvedParams = await searchParams;
  const dateQuery = resolvedParams.date;

  // 1. Fetch available pulses list (with metadata) from backend API
  let availableDates: { id: string; label: string; reviewCount: number }[] = [];
  try {
    const res = await fetch(`${API_URL}/api/pulses`, { cache: 'no-store' });
    if (res.ok) {
      const data: { pulses: PulseMeta[] } = await res.json();
      availableDates = data.pulses.map((p) => ({
        id: p.id,
        label: p.label,
        reviewCount: p.review_count ?? 0,
      }));
    }
  } catch (e) {
    console.error('Failed to fetch pulse list from API:', e);
  }

  if (availableDates.length === 0) {
    return (
      <div className="p-8">
        No pulse reports found. Run the backend <code>generate</code> step first.
      </div>
    );
  }

  // 2. Determine which pulse to display
  const currentId =
    dateQuery && availableDates.find((d) => d.id === dateQuery)
      ? dateQuery
      : availableDates[0].id;

  const currentOption = availableDates.find((d) => d.id === currentId)!;

  // 3. Fetch the selected pulse content from backend API
  let pulseBody = '';
  try {
    const res = await fetch(`${API_URL}/api/pulses/${currentId}`, {
      cache: 'no-store',
    });
    if (res.ok) {
      const data: { content: string } = await res.json();
      pulseBody = parsePulseBody(data.content);
    } else {
      pulseBody = '_Could not load pulse content._';
    }
  } catch (e) {
    console.error('Failed to fetch pulse content from API:', e);
    pulseBody = '_Could not load pulse content._';
  }

  return (
    <main>
      <PulseDashboard
        pulseBody={pulseBody}
        dateRange={currentOption.label}
        reviewCount={currentOption.reviewCount}
        availableDates={availableDates}
        selectedDateId={currentId}
      />
    </main>
  );
}
