import { configureStore } from "@reduxjs/toolkit";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { opportunitiesApi } from "../services/api";
import applicationsReducer from "../features/applications/applicationsSlice";
import opportunitiesReducer from "../features/opportunities/opportunitiesSlice";
import Opportunities from "./Opportunities";

vi.mock("../services/api", () => ({
  opportunitiesApi: { list: vi.fn(() => Promise.resolve({ data: [] })) },
  applicationsApi: { create: vi.fn(() => Promise.resolve({ data: {} })) },
  API_BASE: "http://test",
}));

function renderPage() {
  const store = configureStore({
    reducer: { opportunities: opportunitiesReducer, applications: applicationsReducer },
  });
  render(
    <Provider store={store}>
      <MemoryRouter>
        <Opportunities />
      </MemoryRouter>
    </Provider>
  );
  return store;
}

describe("Opportunities search debounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    opportunitiesApi.list.mockClear();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("fetches once on mount", () => {
    renderPage();
    expect(opportunitiesApi.list).toHaveBeenCalledTimes(1);
  });

  it("coalesces rapid keystrokes into one request after 300ms", async () => {
    renderPage();
    opportunitiesApi.list.mockClear();

    const input = screen.getByPlaceholderText(/search company or role/i);
    for (const chunk of ["g", "go", "gol", "gold", "goldm"]) {
      fireEvent.change(input, { target: { value: chunk } });
      act(() => vi.advanceTimersByTime(60)); // faster than the 300ms debounce
    }
    // No fetch fired while typing.
    expect(opportunitiesApi.list).toHaveBeenCalledTimes(0);

    await act(async () => {
      vi.advanceTimersByTime(300);
    });
    expect(opportunitiesApi.list).toHaveBeenCalledTimes(1);
    expect(opportunitiesApi.list.mock.calls[0][0]).toMatchObject({ search: "goldm" });
  });

  it("non-search filters refetch immediately", () => {
    renderPage();
    opportunitiesApi.list.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Upcoming" }));
    expect(opportunitiesApi.list).toHaveBeenCalledTimes(1);
    expect(opportunitiesApi.list.mock.calls[0][0]).toMatchObject({ upcoming: true });
  });
});
