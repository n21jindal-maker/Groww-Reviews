import { NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const email = body.email;
    
    // Validate email format basic to prevent injection
    if (!email || !email.includes('@')) {
      return NextResponse.json({ error: 'Valid email is required' }, { status: 400 });
    }

    const response = await fetch(`${API_URL}/api/deliver`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
      // Allow up to 2 minutes for delivery to complete
      signal: AbortSignal.timeout(120_000),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok || (data && data.success === false)) {
      console.error("Backend delivery failed:", data);
      return NextResponse.json({ 
        error: 'Failed to trigger delivery pipeline',
        details: data?.error || 'Unknown error'
      }, { status: 500 });
    }

    return NextResponse.json({ 
      success: true, 
      message: 'Delivery pipeline triggered successfully' 
    });

  } catch (error: any) {
    console.error("Failed to trigger delivery pipeline:", error);
    return NextResponse.json({ 
      error: 'Failed to trigger delivery pipeline',
      details: error?.message || 'Unknown error'
    }, { status: 500 });
  }
}
