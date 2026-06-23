import { configureStore } from "@reduxjs/toolkit";
import authReducer from "../features/auth/authSlice";
import opportunitiesReducer from "../features/opportunities/opportunitiesSlice";
import applicationsReducer from "../features/applications/applicationsSlice";
import profileReducer from "../features/profile/profileSlice";
import analyticsReducer from "../features/analytics/analyticsSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    opportunities: opportunitiesReducer,
    applications: applicationsReducer,
    profile: profileReducer,
    analytics: analyticsReducer,
  },
});

export default store;
