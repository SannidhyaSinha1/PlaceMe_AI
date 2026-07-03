import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { opportunitiesApi } from "../../services/api";

export const fetchOpportunities = createAsyncThunk(
  "opportunities/fetch",
  async (_, { getState, rejectWithValue, signal }) => {
    const { filters } = getState().opportunities;
    const params = { sort: filters.sort, limit: filters.limit, offset: filters.offset };
    if (filters.type) params.type = filters.type;
    if (filters.eligibleOnly) params.eligible_only = true;
    if (filters.applied === true) params.applied = true;
    if (filters.upcoming) params.upcoming = true;
    if (filters.search) params.search = filters.search;
    try {
      // The abort signal cancels the HTTP request when a newer fetch starts.
      const { data } = await opportunitiesApi.list(params, signal);
      return data;
    } catch (e) {
      return rejectWithValue(e.response?.data?.detail || "Failed to load opportunities");
    }
  }
);

export const fetchOpportunity = createAsyncThunk("opportunities/fetchOne", async (id) => {
  const { data } = await opportunitiesApi.get(id);
  return data;
});

const initialFilters = {
  type: "",
  eligibleOnly: false,
  applied: null,
  upcoming: false,
  search: "",
  sort: "newest",
  limit: 50,
  offset: 0,
};

const opportunitiesSlice = createSlice({
  name: "opportunities",
  initialState: {
    items: [],
    current: null,
    filters: initialFilters,
    status: "idle",
    error: null,
  },
  reducers: {
    setFilter(state, { payload }) {
      state.filters = { ...state.filters, ...payload, offset: 0 };
    },
    resetFilters(state) {
      state.filters = initialFilters;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchOpportunities.pending, (state, { meta }) => {
        state.status = "loading";
        state.latestRequestId = meta.requestId;
      })
      .addCase(fetchOpportunities.fulfilled, (state, { payload, meta }) => {
        // Ignore out-of-order responses so a stale fetch can't overwrite a newer one.
        if (meta.requestId !== state.latestRequestId) return;
        state.status = "succeeded";
        state.items = payload;
      })
      .addCase(fetchOpportunities.rejected, (state, { payload, meta }) => {
        if (meta.requestId !== state.latestRequestId || meta.aborted) return;
        state.status = "failed";
        state.error = payload;
      })
      .addCase(fetchOpportunity.fulfilled, (state, { payload }) => {
        state.current = payload;
      });
  },
});

export const { setFilter, resetFilters } = opportunitiesSlice.actions;
export default opportunitiesSlice.reducer;
