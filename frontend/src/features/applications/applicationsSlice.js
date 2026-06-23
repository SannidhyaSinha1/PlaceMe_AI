import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { applicationsApi } from "../../services/api";

export const fetchApplications = createAsyncThunk("applications/fetch", async () => {
  const { data } = await applicationsApi.list();
  return data;
});

export const markInterested = createAsyncThunk(
  "applications/create",
  async (opportunityId, { rejectWithValue }) => {
    try {
      const { data } = await applicationsApi.create(opportunityId);
      return data;
    } catch (e) {
      return rejectWithValue(e.response?.data?.detail || "Could not add application");
    }
  }
);

export const updateApplicationStatus = createAsyncThunk(
  "applications/updateStatus",
  async ({ id, status }) => {
    const { data } = await applicationsApi.updateStatus(id, status);
    return data;
  }
);

export const removeApplication = createAsyncThunk("applications/remove", async (id) => {
  await applicationsApi.remove(id);
  return id;
});

const applicationsSlice = createSlice({
  name: "applications",
  initialState: { items: [], status: "idle", error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchApplications.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchApplications.fulfilled, (state, { payload }) => {
        state.status = "succeeded";
        state.items = payload;
      })
      .addCase(markInterested.fulfilled, (state, { payload }) => {
        const idx = state.items.findIndex((a) => a.id === payload.id);
        if (idx >= 0) state.items[idx] = payload;
        else state.items.unshift(payload);
      })
      .addCase(updateApplicationStatus.fulfilled, (state, { payload }) => {
        const idx = state.items.findIndex((a) => a.id === payload.id);
        if (idx >= 0) state.items[idx] = payload;
      })
      .addCase(removeApplication.fulfilled, (state, { payload }) => {
        state.items = state.items.filter((a) => a.id !== payload);
      });
  },
});

export default applicationsSlice.reducer;
