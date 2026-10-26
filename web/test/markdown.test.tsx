import { render, screen } from "@testing-library/react";

import { Markdown } from "../src/shared/ui/Markdown";

describe("Markdown", () => {
  it("renders headings, tables and lists from the SteerCo pack, and never HTML", () => {
    render(
      <Markdown
        source={
          "# SteerCo\n\n## KPIs\n\n| KPI | Now |\n| --- | --- |\n| Red flags | **98%** |\n\n- one\n- <b>two</b>\n"
        }
      />,
    );
    expect(screen.getByRole("heading", { name: "SteerCo" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "KPI" })).toBeInTheDocument();
    expect(screen.getByText("98%").tagName).toBe("STRONG");
    expect(screen.getByText("<b>two</b>")).toBeInTheDocument();
  });
});
