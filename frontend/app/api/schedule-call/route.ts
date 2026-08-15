import { NextResponse } from 'next/server';
import { execSync } from 'child_process';
import path from 'path';

export async function GET() {
  try {
    const backendDir = path.resolve(process.cwd(), '../backend');
    const pyScript = `import json, db; print(json.dumps(db.get_all_scheduled_calls()))`;
    const output = execSync(`uv run python -c "${pyScript}"`, {
      cwd: backendDir,
      encoding: 'utf-8',
    });
    const calls = JSON.parse(output.trim());
    return NextResponse.json({ success: true, calls });
  } catch (error: any) {
    console.error('API /api/schedule-call GET error:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { participantName, phoneNumber, scheduledAtISO } = body;

    if (!participantName || !phoneNumber || !scheduledAtISO) {
      return NextResponse.json(
        {
          success: false,
          error: 'Learner Name, SIP Address, and Scheduled Time are required.',
        },
        { status: 400 }
      );
    }

    const backendDir = path.resolve(process.cwd(), '../backend');
    // Base64 encode the payload to safely pass across Windows cmd/PowerShell shell boundaries
    const payloadJson = JSON.stringify({
      name: String(participantName),
      phone: String(phoneNumber),
      scheduledAt: String(scheduledAtISO),
    });
    const base64Payload = Buffer.from(payloadJson, 'utf-8').toString('base64');

    const pyScript = `import json, base64, db; data=json.loads(base64.b64decode('${base64Payload}').decode('utf-8')); print(json.dumps(db.schedule_outbound_call(data['name'], data['phone'], data['scheduledAt'])))`;

    const output = execSync(`uv run python -c "${pyScript}"`, {
      cwd: backendDir,
      encoding: 'utf-8',
    });

    const result = JSON.parse(output.trim());
    return NextResponse.json({ success: true, call: result });
  } catch (error: any) {
    console.error('API /api/schedule-call POST error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to schedule outbound call' },
      { status: 500 }
    );
  }
}
