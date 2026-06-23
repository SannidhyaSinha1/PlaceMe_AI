import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { analyticsApi } from "../../services/api";

export const fetchDashboard = createAsyncThunk("analytics/dashboard", async () => {
  const { data } = await analyticsApi.dashboard();
  return data;
});

export const fetchCharts = createAsyncThunk("analytics/charts", async (theme = "light") => {
  const { data } = await analyticsApi.charts(theme);
  return data;
});

const analyticsSlice = createSlice({
  name: "analytics",
  initialState: { dashboard: null, charts: null, status: "idle" },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboard.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchDashboard.fulfilled, (state, { payload }) => {
        state.status = "succeeded";
        state.dashboard = payload;
      })
      .addCase(fetchCharts.fulfilled, (state, { payload }) => {
        state.charts = payload;
      });
  },
});

export default analyticsSlice.reducer;
