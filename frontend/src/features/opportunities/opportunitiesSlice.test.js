import { describe, expect, it } from "vitest";
import reducer, { fetchOpportunities, setFilter } from "./opportunitiesSlice";

const init = () => reducer(undefined, { type: "@@INIT" });

const pending = (requestId) => ({
  type: fetchOpportunities.pending.type,
  meta: { requestId },
});
const fulfilled = (requestId, payload) => ({
  type: fetchOpportunities.fulfilled.type,
  payload,
  meta: { requestId },
});
const rejected = (requestId, payload, aborted = false) => ({
  type: fetchOpportunities.rejected.type,
  payload,
  meta: { requestId, aborted },
});

describe("opportunities stale-response guard", () => {
  it("applies the latest response", () => {
    let s = init();
    s = reducer(s, pending("req-1"));
    s = reducer(s, fulfilled("req-1", [{ id: 1 }]));
    expect(s.items).toEqual([{ id: 1 }]);
    expect(s.status).toBe("succeeded");
  });

  it("ignores a stale response arriving after a newer request started", () => {
    let s = init();
    s = reducer(s, pending("req-old"));
    s = reducer(s, pending("req-new"));
    // Old response lands late — must NOT overwrite.
    s = reducer(s, fulfilled("req-old", [{ id: 999, stale: true }]));
    expect(s.items).toEqual([]);
    expect(s.status).toBe("loading");
    // Fresh response applies.
    s = reducer(s, fulfilled("req-new", [{ id: 2 }]));
    expect(s.items).toEqual([{ id: 2 }]);
  });

  it("ignores stale and aborted rejections", () => {
    let s = init();
    s = reducer(s, pending("req-a"));
    s = reducer(s, pending("req-b"));
    s = reducer(s, rejected("req-a", "boom"));
    expect(s.status).toBe("loading"); // stale rejection ignored
    s = reducer(s, rejected("req-b", "boom", true));
    expect(s.status).toBe("loading"); // aborts never mark failure
    s = reducer(s, pending("req-c"));
    s = reducer(s, rejected("req-c", "real failure"));
    expect(s.status).toBe("failed");
    expect(s.error).toBe("real failure");
  });
});

describe("filters", () => {
  it("setFilter merges a patch and resets offset", () => {
    let s = init();
    s = reducer(s, setFilter({ offset: 50 }));
    s = reducer(s, setFilter({ search: "acme" }));
    expect(s.filters.search).toBe("acme");
    expect(s.filters.offset).toBe(0);
  });
});
