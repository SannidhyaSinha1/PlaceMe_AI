import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { authApi } from "../../services/api";

const tokenFromStorage = localStorage.getItem("token");

export const login = createAsyncThunk("auth/login", async ({ email, password }, { rejectWithValue }) => {
  try {
    const { data } = await authApi.login(email, password);
    localStorage.setItem("token", data.access_token);
    return data;
  } catch (e) {
    return rejectWithValue(e.response?.data?.detail || "Login failed");
  }
});

export const register = createAsyncThunk("auth/register", async ({ email, password }, { rejectWithValue }) => {
  try {
    const { data } = await authApi.register(email, password);
    localStorage.setItem("token", data.access_token);
    return data;
  } catch (e) {
    return rejectWithValue(e.response?.data?.detail || "Registration failed");
  }
});

export const fetchMe = createAsyncThunk("auth/me", async (_, { rejectWithValue }) => {
  try {
    const { data } = await authApi.me();
    return data;
  } catch {
    return rejectWithValue("Session expired");
  }
});

const authSlice = createSlice({
  name: "auth",
  initialState: {
    token: tokenFromStorage || null,
    user: null,
    status: "idle",
    error: null,
  },
  reducers: {
    logout(state) {
      localStorage.removeItem("token");
      state.token = null;
      state.user = null;
    },
  },
  extraReducers: (builder) => {
    const onAuth = (state, { payload }) => {
      state.token = payload.access_token;
      state.user = payload.user;
      state.status = "succeeded";
      state.error = null;
    };
    builder
      .addCase(login.fulfilled, onAuth)
      .addCase(register.fulfilled, onAuth)
      .addCase(fetchMe.fulfilled, (state, { payload }) => {
        state.user = payload;
      })
      .addCase(fetchMe.rejected, (state) => {
        state.token = null;
        state.user = null;
      });
    [login, register].forEach((thunk) => {
      builder
        .addCase(thunk.pending, (state) => {
          state.status = "loading";
          state.error = null;
        })
        .addCase(thunk.rejected, (state, { payload }) => {
          state.status = "failed";
          state.error = payload;
        });
    });
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
