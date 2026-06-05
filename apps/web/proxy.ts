import { NextResponse, type NextRequest } from "next/server";

const REALM = "Trading System";

export function proxy(request: NextRequest) {
  if (!basicAuthRequired()) {
    return NextResponse.next();
  }

  const username = process.env.BASIC_AUTH_USERNAME;
  const password = process.env.BASIC_AUTH_PASSWORD;
  if (!username || !password) {
    return new NextResponse("Basic Auth is not configured", { status: 500 });
  }

  const credentials = parseBasicAuth(request.headers.get("authorization"));
  if (credentials?.username === username && credentials.password === password) {
    return NextResponse.next();
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": `Basic realm="${REALM}"`
    }
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"]
};

function basicAuthRequired() {
  return envBool(process.env.CLOUD_MODE) || envBool(process.env.BASIC_AUTH_ENABLED);
}

function envBool(value: string | undefined) {
  return ["1", "true", "yes", "on"].includes(value?.trim().toLowerCase() ?? "");
}

function parseBasicAuth(value: string | null) {
  if (!value?.toLowerCase().startsWith("basic ")) {
    return null;
  }
  try {
    const decoded = atob(value.slice(6).trim());
    const separator = decoded.indexOf(":");
    if (separator < 0) {
      return null;
    }
    return {
      username: decoded.slice(0, separator),
      password: decoded.slice(separator + 1)
    };
  } catch {
    return null;
  }
}
