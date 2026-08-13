import { NextResponse } from 'next/server';
import { execSync } from 'child_process';
import path from 'path';

export async function GET() {
  try {
    const backendDir = path.resolve(process.cwd(), '../backend');
    const pyScript = `import json, db; print(json.dumps({'analytics': db.get_call_analytics(), 'recent_logs': db.get_recent_call_logs(20)}))`;
    const output = execSync(`uv run python -c "${pyScript}"`, {
      cwd: backendDir,
      encoding: 'utf-8',
    });
    const data = JSON.parse(output.trim());
    return NextResponse.json({ success: true, ...data });
  } catch (error: any) {
    console.error('API /api/analytics GET error:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
