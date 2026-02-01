import { NextRequest, NextResponse } from "next/server";

const HLS_BACKEND =
  process.env.HLS_PROXY_TARGET || "http://localhost:8080";

// Minimal HLS playlist when no stream is active yet (backend 404)
const STUB_PLAYLIST = `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:3
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-ENDLIST
`;

/**
 * Proxies HLS requests to the RTMP server so the Live tab uses same-origin URLs.
 * If the backend returns 404 (no stream yet), returns a stub playlist so the UI
 * doesn't show a hard error and can show "Waiting for stream".
 */
export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const pathStr = path?.join("/") ?? "";
  const url = `${HLS_BACKEND}/${pathStr}`;

  try {
    const res = await fetch(url, {
      cache: "no-store",
      headers: { Accept: "*/*" },
    });

    // No stream active yet: return stub playlist so player doesn't fatal-error
    if (res.status === 404 && pathStr.endsWith(".m3u8")) {
      return new NextResponse(STUB_PLAYLIST, {
        status: 200,
        headers: {
          "Content-Type": "application/vnd.apple.mpegurl",
          "Cache-Control": "no-cache, no-store",
          "Access-Control-Allow-Origin": "*",
          "X-HLS-Stub": "1",
        },
      });
    }

    const contentType =
      res.headers.get("content-type") || "application/octet-stream";

    return new NextResponse(res.body, {
      status: res.status,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-cache, no-store",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (err) {
    console.error("[HLS proxy] fetch failed:", err);
    return NextResponse.json(
      { error: "HLS server unreachable. Is run_dji_live_rtmp.sh running?" },
      { status: 502 }
    );
  }
}
