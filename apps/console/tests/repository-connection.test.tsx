import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RepositoryConnection } from "@/components/repository-connection";

const repositories = [
  {
    id: 101,
    fullName: "octocat/alpha",
    defaultBranch: "main",
    private: true,
    archived: false,
    htmlUrl: "https://github.com/octocat/alpha",
  },
  {
    id: 202,
    fullName: "octocat/beta",
    defaultBranch: "trunk",
    private: false,
    archived: false,
    htmlUrl: "https://github.com/octocat/beta",
  },
];

describe("Repository connection", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  });

  it("offers the GitHub App install flow only when it is configured", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          configured: true,
          connected: false,
          actionsEnabled: false,
          accountLogin: null,
          repositories: [],
          selectedRepository: null,
        }),
      ),
    );

    render(<RepositoryConnection />);

    const connect = await screen.findByRole("link", { name: "Connect GitHub" });
    expect(connect).toHaveAttribute("href", "/api/integrations/github/install");
    expect(
      screen.getByText(
        "Issue creation is off. Audits will only record a proposed action.",
      ),
    ).toBeVisible();
  });

  it("selects only a repository returned by the verified installation", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({
          configured: true,
          connected: true,
          actionsEnabled: true,
          accountLogin: "octocat",
          repositories,
          selectedRepository: null,
        }),
      )
      .mockResolvedValueOnce(
        Response.json({
          configured: true,
          connected: true,
          actionsEnabled: true,
          accountLogin: "octocat",
          repositories,
          selectedRepository: repositories[1],
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<RepositoryConnection />);
    const select = await screen.findByLabelText("Selected repository");
    expect(
      screen.getByText(
        "Select a repository before running an action-ready audit.",
      ),
    ).toBeVisible();
    expect(select).toHaveClass("min-w-0", "flex-1");
    expect(select.parentElement).toHaveClass("w-full", "flex-wrap");

    fireEvent.change(select, {
      target: { value: "202" },
    });

    expect(
      await screen.findByRole("link", { name: /octocat\/beta/ }),
    ).toHaveAttribute("href", "https://github.com/octocat/beta");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      method: "PUT",
      body: JSON.stringify({ repositoryId: 202 }),
    });
    expect(
      screen.getByText(
        "Verified draft PRs and fallback issues are enabled for this repository.",
      ),
    ).toBeVisible();
  });

  it("returns OAuth failures to a recoverable dashboard state", async () => {
    window.history.replaceState({}, "", "/?github=error");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          configured: true,
          connected: false,
          actionsEnabled: true,
          accountLogin: null,
          repositories: [],
          selectedRepository: null,
        }),
      ),
    );

    render(<RepositoryConnection />);

    expect(
      await screen.findByText("GitHub could not be connected. Try again."),
    ).toHaveAttribute("role", "alert");
    expect(window.location.search).toBe("");
  });
});
