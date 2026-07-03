import { describe, expect, it } from "vitest";
import reducer, { fetchMe, login, logout } from "./authSlice";

const init = () => reducer(undefined, { type: "@@INIT" });

describe("auth slice", () => {
  it("stores token and user on login", () => {
    const s = reducer(init(), {
      type: login.fulfilled.type,
      payload: { access_token: "tok-123", user: { id: 1, email: "a@b.co" } },
    });
    expect(s.token).toBe("tok-123");
    expect(s.user.email).toBe("a@b.co");
    expect(s.status).toBe("succeeded");
  });

  it("records the error on failed login", () => {
    const s = reducer(init(), { type: login.rejected.type, payload: "Invalid credentials" });
    expect(s.status).toBe("failed");
    expect(s.error).toBe("Invalid credentials");
    expect(s.token).toBeNull();
  });

  it("clears the session when /auth/me fails (expired token)", () => {
    let s = reducer(init(), {
      type: login.fulfilled.type,
      payload: { access_token: "tok", user: { id: 1 } },
    });
    s = reducer(s, { type: fetchMe.rejected.type });
    expect(s.token).toBeNull();
    expect(s.user).toBeNull();
  });

  it("logout clears token, user and localStorage", () => {
    localStorage.setItem("token", "tok");
    let s = reducer(init(), {
      type: login.fulfilled.type,
      payload: { access_token: "tok", user: { id: 1 } },
    });
    s = reducer(s, logout());
    expect(s.token).toBeNull();
    expect(localStorage.getItem("token")).toBeNull();
  });
});
