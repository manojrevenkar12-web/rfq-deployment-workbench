import type { Problem } from "./types";

const TOKEN_KEY = "rdw.token";

/** The API token, when the API asks for one (RDW_API_TOKEN). Kept for this browser tab only. */
export const token = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(value: string) {
    try {
      sessionStorage.setItem(TOKEN_KEY, value.trim());
    } catch {
      /* private mode: the token lives until reload */
    }
  },
};

/** An API failure with what the API said about it (problem details) and whether trying again may help. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly title: string,
    readonly detail?: string,
  ) {
    super(detail ? `${title}: ${detail}` : title);
  }

  get retryable() {
    return this.status === 0 || this.status === 429 || this.status >= 500;
  }

  get needsToken() {
    return this.status === 401;
  }
}

type Body = { json: unknown } | { form: FormData } | undefined;

async function send(
  method: string,
  path: string,
  body?: Body,
  accept = "application/json",
): Promise<Response> {
  const headers: Record<string, string> = { accept };
  const t = token.get();
  if (t) headers["authorization"] = `Bearer ${t}`;
  let payload: BodyInit | undefined;
  if (body && "json" in body) {
    headers["content-type"] = "application/json";
    payload = JSON.stringify(body.json);
  } else if (body && "form" in body) {
    payload = body.form;
  }
  let response: Response;
  try {
    response = await fetch(path, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "The workbench API cannot be reached", "Check that `rdw serve` is running.");
  }
  if (!response.ok) {
    let problem: Partial<Problem> = {};
    try {
      problem = (await response.json()) as Problem;
    } catch {
      /* no body */
    }
    const title =
      problem.title ??
      (response.status === 401 ? "The API needs a token" : `The API answered ${response.status}`);
    throw new ApiError(response.status, title, problem.detail);
  }
  return response;
}

export const api = {
  get: async <T>(path: string) => (await (await send("GET", path)).json()) as T,
  text: async (path: string) => (await send("GET", path, undefined, "text/plain")).text(),
  blob: async (path: string) => (await send("GET", path, undefined, "*/*")).blob(),
  post: async <T>(path: string, json: unknown) => (await (await send("POST", path, { json })).json()) as T,
  put: async <T>(path: string, json: unknown) => (await (await send("PUT", path, { json })).json()) as T,
  upload: async <T>(path: string, form: FormData) => (await (await send("POST", path, { form })).json()) as T,
};
