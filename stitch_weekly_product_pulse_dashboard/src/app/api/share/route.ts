import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import util from 'util';
import path from 'path';

const execPromise = util.promisify(exec);

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const email = body.email;
    
    // Validate email format basic to prevent injection
    if (!email || !email.includes('@')) {
      return NextResponse.json({ error: 'Valid email is required' }, { status: 400 });
    }

    // Determine the path to the python project root
    const projectRoot = path.join(process.cwd(), '..');
    
    // We execute the delivery step from the main project root
    // This will spawn the Python process to run the MCP delivery pipeline
    const command = `python -m src.main --step deliver --email "${email}"`;
    
    console.log(`Executing delivery command in: ${projectRoot}`);
    
    const { stdout, stderr } = await execPromise(command, { cwd: projectRoot });
    
    console.log("Delivery stdout:", stdout);
    if (stderr) {
      console.warn("Delivery stderr:", stderr);
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
