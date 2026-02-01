import { NextResponse } from "next/server";

/**
 * Returns the live DJI stream URL for the UI Live tab.
 * Defaults to the same-origin proxy /api/hls/... so the browser avoids CORS.
 * Override with NEXT_PUBLIC_LIVE_STREAM_URL (e.g. direct http://localhost:8080/...).
 */
export async function GET(request: Request) {
  if (process.env.NEXT_PUBLIC_LIVE_STREAM_URL) {
    return NextResponse.json({
      streamUrl: process.env.NEXT_PUBLIC_LIVE_STREAM_URL,
    });
  }
  const host = request.headers.get("host") || "localhost:3000";
  // Stream name must match RTMP URL: rtmp://.../live/STREAM_KEY → HLS at /live/STREAM_KEY/index.m3u8
  const streamKey = process.env.LIVE_STREAM_KEY || "djidji";
  const streamUrl = `http://${host}/api/hls/live/${streamKey}/index.m3u8`;
  return NextResponse.json({ streamUrl });
}
