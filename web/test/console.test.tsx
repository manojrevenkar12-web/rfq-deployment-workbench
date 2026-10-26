import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { fx, voltaroRoutes } from "./fixtures";
import { clone, json, problem, renderAt, stubApi } from "./harness";

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

describe("portfolio", () => {
  it("shows every deployment with its health, value and next step", async () => {
    stubApi(voltaroRoutes());
    renderAt("/");
    const table = await screen.findByRole("region", { name: "Customers" });
    for (const c of fx.portfolio.customers) {
      expect(within(table).getByRole("link", { name: c.name })).toHaveAttribute("href", `/c/${c.id}`);
    }
    expect(within(table).getAllByText("At risk").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { level: 1, name: "Deployments" })).toBeInTheDocument();
  });

  it("puts the held-out first run next to the scores the agents were built on", async () => {
    stubApi(voltaroRoutes());
    renderAt("/");
    const heldout = await screen.findByRole("region", { name: /Held-out set v1/ });
    const recall = fx.heldout[0]!.customers.voltaro!.metrics.requirement_recall!;
    expect(
      within(heldout).getByText(new RegExp(`\\(${recall.right} of ${recall.of}\\)`)),
    ).toBeInTheDocument();
    expect(screen.getByText(/Where the \d+ misses come from/)).toBeInTheDocument();
  });

  it("shows a skeleton while loading", async () => {
    let release: (v: Response) => void = () => {};
    stubApi({
      ...voltaroRoutes(),
      "GET /api/portfolio": () => new Promise<Response>((r) => (release = r)),
    });
    renderAt("/");
    expect(await screen.findByRole("status", { name: "Loading the deployments" })).toBeInTheDocument();
    release(json(fx.portfolio));
    expect(await screen.findByRole("region", { name: "Customers" })).toBeInTheDocument();
  });

  it("says what failed and retries", async () => {
    let fail = true;
    stubApi({
      ...voltaroRoutes(),
      "GET /api/portfolio": () => (fail ? problem(503, "The database is starting") : json(fx.portfolio)),
    });
    renderAt("/");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The database is starting");
    fail = false;
    await userEvent.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("region", { name: "Customers" })).toBeInTheDocument();
  });

  it("explains what to do when there are no customers", async () => {
    stubApi({ ...voltaroRoutes(), "GET /api/portfolio": { ...clone(fx.portfolio), customers: [] } });
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "No customers yet" })).toBeInTheDocument();
  });

  it("asks for the API token when the API wants one and sends it from then on", async () => {
    stubApi({
      ...voltaroRoutes(),
      "GET /api/portfolio": (_u: string, init?: RequestInit) =>
        (init?.headers as Record<string, string>)["authorization"] === "Bearer s3cret"
          ? json(fx.portfolio)
          : problem(401, "a valid bearer token is required"),
    });
    renderAt("/");
    const field = await screen.findByLabelText("API token");
    await userEvent.type(field, "s3cret");
    await userEvent.click(screen.getByRole("button", { name: "Use token" }));
    expect(await screen.findByRole("region", { name: "Customers" })).toBeInTheDocument();
    expect(sessionStorage.getItem("rdw.token")).toBe("s3cret");
  });
});

describe("customer overview", () => {
  it("leads with the summary, the next steps and the plan", async () => {
    stubApi(voltaroRoutes());
    renderAt("/c/voltaro");
    expect(
      await screen.findByRole("heading", { level: 1, name: fx.voltaro.customer.name }),
    ).toBeInTheDocument();
    expect(screen.getByText(fx.voltaro.summary)).toBeInTheDocument();
    expect(screen.getByText(fx.voltaro.next_steps[0]!.text)).toBeInTheDocument();
    expect(screen.getByText(/overdue by 11 days/)).toBeInTheDocument();
    expect(screen.getByText(/Live since 3 Aug 2026/)).toBeInTheDocument();
  });

  it("records a decision and shows it", async () => {
    const routes = voltaroRoutes();
    let current = clone(fx.voltaro);
    routes["GET /api/customers/voltaro"] = () => current;
    routes["POST /api/customers/voltaro/decisions"] = (_u: string, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body)) as { decision: string; by: string };
      const row = { date: "2026-10-26", decision: body.decision, by: body.by, source: "workbench" };
      current = { ...current, decisions: [...current.decisions, row] };
      return row;
    };
    const calls = stubApi(routes);
    renderAt("/c/voltaro");
    await userEvent.type(
      await screen.findByLabelText("Decision"),
      "Engineering pilots red flags on 10 tenders.",
    );
    await userEvent.type(screen.getByLabelText("Decided by"), "Jonas Reiter");
    await userEvent.click(screen.getByRole("button", { name: "Record decision" }));
    expect(await screen.findByText("Engineering pilots red flags on 10 tenders.")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      decision: "Engineering pilots red flags on 10 tenders.",
      by: "Jonas Reiter",
    });
  });

  it("opens the SteerCo pack on request", async () => {
    const calls = stubApi(voltaroRoutes());
    renderAt("/c/voltaro");
    await screen.findByText(fx.voltaro.summary);
    expect(calls.some((c) => c.path.endsWith("/steerco"))).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Show pack" }));
    expect(await screen.findByRole("heading", { name: /SteerCo: Voltaro/ })).toBeInTheDocument();
  });

  it("shows an unknown customer as a problem, not an empty page", async () => {
    stubApi({ ...voltaroRoutes(), "GET /api/customers/nobody": problem(404, "no customer nobody") });
    renderAt("/c/nobody");
    expect(await screen.findByRole("alert")).toHaveTextContent("no customer nobody");
  });
});

describe("process", () => {
  it("draws where the days go and switches to the replay with the agents", async () => {
    stubApi(voltaroRoutes());
    renderAt("/c/voltaro/process");
    const strip = await screen.findByRole("img", { name: /The average tender today/ });
    expect(strip).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "With the agents in scope" }));
    expect(await screen.findByRole("img", { name: /with the agents in scope/ })).toBeInTheDocument();
    expect(screen.getByText(/half of all bids would leave within 2.9 days/)).toBeInTheDocument();
  });

  it("compares the months since go-live with the plan", async () => {
    stubApi(voltaroRoutes());
    renderAt("/c/voltaro/process");
    const live = await screen.findByRole("region", { name: "Effort per activity since go-live" });
    expect(within(live).getAllByText("Behind the plan").length).toBeGreaterThan(0);
  });

  it("does not ask for the go-live comparison of a customer that is not live", async () => {
    const routes = {
      "GET /api/portfolio": fx.portfolio,
      "GET /api/customers/gleiswerk": fx.gleiswerk,
      "GET /api/customers/gleiswerk/discovery": fx.discovery,
      "POST /api/customers/gleiswerk/value": fx.value,
    };
    const calls = stubApi(routes);
    renderAt("/c/gleiswerk/process");
    await screen.findByRole("img", { name: /The average tender today/ });
    expect(calls.some((c) => c.path.endsWith("/live"))).toBe(false);
    expect(screen.getByText(/go-live planned/)).toBeInTheDocument();
  });

  it("explains an empty quote process", async () => {
    stubApi({
      ...voltaroRoutes(),
      "GET /api/customers/voltaro/discovery": { ...clone(fx.discovery), cases: 0 },
    });
    renderAt("/c/voltaro/process");
    expect(await screen.findByRole("heading", { name: "No quote process yet" })).toBeInTheDocument();
  });
});

describe("tenders", () => {
  it("filters by recommendation and search, and offers a way back from nothing", async () => {
    stubApi(voltaroRoutes());
    renderAt("/c/voltaro/tenders");
    const table = await screen.findByRole("region", { name: "Tenders" });
    expect(within(table).getAllByRole("row")).toHaveLength(fx.tenders.length + 1);
    const noBids = fx.tenders.filter((t) => t.decision === "no_bid").length;
    await userEvent.click(screen.getByRole("radio", { name: `No bid (${noBids})` }));
    expect(within(screen.getByRole("region", { name: "Tenders" })).getAllByRole("row")).toHaveLength(
      noBids + 1,
    );
    await userEvent.type(screen.getByLabelText("Search tenders"), "zzzz");
    expect(screen.getByRole("heading", { name: "No tender matches" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show all tenders" }));
    expect(within(screen.getByRole("region", { name: "Tenders" })).getAllByRole("row")).toHaveLength(
      fx.tenders.length + 1,
    );
  });

  it("reads a new tender from the inbox without adding it to the history", async () => {
    const routes = voltaroRoutes();
    routes["POST /api/customers/voltaro/inbox"] = { ...clone(fx.tender), tender_id: "IN-1234" };
    const calls = stubApi(routes);
    renderAt("/c/voltaro/tenders");
    await screen.findByRole("region", { name: "Tenders" });
    const file = new File(["%PDF"], "spec.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Tender documents"), file);
    expect(await screen.findByText(/IN-1234\./)).toBeInTheDocument();
    const sent = calls.find((c) => c.path.endsWith("/inbox"));
    expect(sent?.body).toBeInstanceOf(FormData);
    expect((sent?.body as FormData).getAll("files")).toHaveLength(1);
    expect(screen.queryByLabelText("Reviewing as")).not.toBeInTheDocument();
  });

  it("shows why an upload was refused", async () => {
    stubApi({
      ...voltaroRoutes(),
      "POST /api/customers/voltaro/inbox": problem(415, "notes.docx: send PDF, Excel, e-mail or text"),
    });
    renderAt("/c/voltaro/tenders");
    await screen.findByRole("region", { name: "Tenders" });
    await userEvent.upload(screen.getByLabelText("Tender documents"), new File(["x"], "notes.pdf"));
    expect(await screen.findByRole("alert")).toHaveTextContent("send PDF, Excel, e-mail or text");
  });
});

describe("tender review", () => {
  it("puts the buyer's words beside the agents' reading, red flags first", async () => {
    stubApi(voltaroRoutes());
    renderAt("/c/voltaro/tenders/VO-2026-001");
    expect(await screen.findByRole("heading", { name: fx.tender.subject })).toBeInTheDocument();
    const flags = fx.tender.requirements.filter((r) => r.red_flag);
    expect(screen.getAllByRole("group", { name: /^Review / })).toHaveLength(flags.length);
    expect(screen.getByText(flags[0]!.source.text)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "All" }));
    expect(screen.getAllByRole("group", { name: /^Review / })).toHaveLength(fx.tender.requirements.length);
  });

  it("needs a name before a review, then records a correction", async () => {
    const routes = voltaroRoutes();
    const r = fx.tender.requirements.find((x) => x.red_flag)!;
    routes[`POST /api/customers/voltaro/tenders/VO-2026-001/requirements/${r.id}/review`] = (
      _u: string,
      init?: RequestInit,
    ) => {
      const body = JSON.parse(String(init?.body)) as { verdict: string; reviewer: string };
      return {
        customer: "voltaro",
        tender: "VO-2026-001",
        requirement: r.id,
        kind: r.kind,
        action: body.verdict === r.verdict ? "confirm" : "correct",
        agent_verdict: r.verdict,
        verdict: body.verdict,
        comment: "",
        reviewer: body.reviewer,
        at: "2026-10-26T10:00:00+00:00",
      };
    };
    const calls = stubApi(routes);
    renderAt("/c/voltaro/tenders/VO-2026-001");
    const group = await screen.findByRole("group", { name: `Review ${r.id}` });
    expect(within(group).getByRole("button", { name: "Confirm" })).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Reviewing as"), "Sabine Kraus");
    await userEvent.click(within(group).getByRole("button", { name: "Change to clarify" }));
    expect(await screen.findByText("Changed to clarify by Sabine Kraus")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      verdict: "clarify",
      reviewer: "Sabine Kraus",
      comment: "",
    });
    expect(localStorage.getItem("rdw.reviewer")).toBe("Sabine Kraus");
  });

  it("shows the clarification letter on request", async () => {
    stubApi({
      ...voltaroRoutes(),
      "GET /api/customers/voltaro/tenders/VO-2026-001/letter": () =>
        new Response("Betreff: Bieterfragen zu VO-2026-001", { headers: { "content-type": "text/plain" } }),
    });
    renderAt("/c/voltaro/tenders/VO-2026-001");
    await userEvent.click(await screen.findByRole("button", { name: "Show clarification letter" }));
    expect(await screen.findByText(/Bieterfragen zu VO-2026-001/)).toBeInTheDocument();
  });
});

describe("readiness", () => {
  it("shows each agent's level and quotes the held-out run beside it", async () => {
    stubApi(voltaroRoutes());
    renderAt("/c/voltaro/readiness");
    expect(await screen.findByRole("heading", { name: "Red-flag detection" })).toBeInTheDocument();
    expect(screen.getAllByRole("meter")).toHaveLength(6);
    expect(await screen.findByText(/On 8 held-out tenders/)).toBeInTheDocument();
  });

  it("splits the misses between the deployment and the platform", async () => {
    stubApi(voltaroRoutes());
    renderAt("/c/voltaro/readiness");
    const deployment = fx.readiness.misses.filter((m) => m.owner === "deployment").length;
    expect(await screen.findByRole("radio", { name: `Deployment (${deployment})` })).toBeChecked();
    await userEvent.click(screen.getByRole("radio", { name: /Platform/ }));
    expect(screen.getByText(/No miss belongs to the platform/)).toBeInTheDocument();
  });
});

describe("value case", () => {
  it("recalculates when the scope changes and saves assumptions", async () => {
    const routes = voltaroRoutes();
    routes["PUT /api/customers/voltaro/assumptions"] = { annual_fee: 80000 };
    const calls = stubApi(routes);
    renderAt("/c/voltaro/value");
    expect(await screen.findByText(fx.value.statement)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /Configuration/ }));
    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.method === "POST" &&
            Array.isArray((c.body as { scope: string[] | null }).scope) &&
            !(c.body as { scope: string[] }).scope.includes("configuration"),
        ),
      ).toBe(true),
    );
    const fee = screen.getByLabelText("Annual fee");
    await userEvent.clear(fee);
    await userEvent.type(fee, "80000");
    const save = screen.getByRole("button", { name: /Save assumptions/ });
    await waitFor(() => expect(save).toBeEnabled());
    await userEvent.click(save);
    await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ annual_fee: 80000 }));
  });
});
