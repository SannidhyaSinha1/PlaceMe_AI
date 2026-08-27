import { configureStore } from "@reduxjs/toolkit";
import authReducer from "../features/auth/authSlice";
import opportunitiesReducer from "../features/opportunities/opportunitiesSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    opportunities: opportunitiesReducer,
  },
});

export default store;
