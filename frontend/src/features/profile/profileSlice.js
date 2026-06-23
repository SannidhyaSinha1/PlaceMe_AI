import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { profileApi } from "../../services/api";

export const fetchProfile = createAsyncThunk("profile/fetch", async () => {
  const { data } = await profileApi.get();
  return data;
});

export const saveProfile = createAsyncThunk("profile/save", async (payload, { rejectWithValue }) => {
  try {
    const { data } = await profileApi.update(payload);
    return data;
  } catch (e) {
    return rejectWithValue(e.response?.data?.detail || "Save failed");
  }
});

export const uploadResume = createAsyncThunk("profile/uploadResume", async (file, { rejectWithValue }) => {
  try {
    const { data } = await profileApi.uploadResume(file);
    return data;
  } catch (e) {
    return rejectWithValue(e.response?.data?.detail || "Upload failed");
  }
});

const profileSlice = createSlice({
  name: "profile",
  initialState: { data: null, status: "idle", saving: false, error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchProfile.fulfilled, (state, { payload }) => {
        state.data = payload;
        state.status = "succeeded";
      })
      .addCase(saveProfile.pending, (state) => {
        state.saving = true;
        state.error = null;
      })
      .addCase(saveProfile.fulfilled, (state, { payload }) => {
        state.saving = false;
        state.data = payload;
      })
      .addCase(saveProfile.rejected, (state, { payload }) => {
        state.saving = false;
        state.error = payload;
      })
      .addCase(uploadResume.fulfilled, (state, { payload }) => {
        state.data = payload;
      });
  },
});

export default profileSlice.reducer;
