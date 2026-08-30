const FUNCTION_NAME = "nexus-database-api";

const RESPONSE_HEADERS = {
  "Cache-Control": "no-store",
  "Content-Type": "application/json; charset=utf-8",
  "X-Content-Type-Options": "nosniff",
};

Deno.serve((_request: Request) =>
  new Response(
    JSON.stringify({
      error: "function_quarantined",
      function: FUNCTION_NAME,
      status: "gone",
    }),
    {
      status: 410,
      headers: RESPONSE_HEADERS,
    },
  )
);
