import { NextResponse } from 'next/server';
import { execSync } from 'child_process';
import path from 'path';

export async function GET() {
  try {
    const backendDir = path.resolve(process.cwd(), '../backend');
    const pyScript = `import json, db; print(json.dumps(db.get_all_escalation_tickets()))`;
    const output = execSync(`uv run python -c "${pyScript}"`, {
      cwd: backendDir,
      encoding: 'utf-8',
    });
    const escalations = JSON.parse(output.trim());
    return NextResponse.json({ success: true, escalations });
  } catch (error: any) {
    console.error('API /api/escalations GET error:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { reference_id, status } = body;

    if (!reference_id || !status) {
      return NextResponse.json(
        { success: false, error: 'reference_id and status are required' },
        { status: 400 }
      );
    }

    const backendDir = path.resolve(process.cwd(), '../backend');
    const pyScript = `import db; print(db.update_escalation_status('${reference_id}', '${status}'))`;
    execSync(`uv run python -c "${pyScript}"`, {
      cwd: backendDir,
      encoding: 'utf-8',
    });

    return NextResponse.json({ success: true, reference_id, status: status.toUpperCase() });
  } catch (error: any) {
    console.error('API /api/escalations POST error:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
