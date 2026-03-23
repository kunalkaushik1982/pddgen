/**
 * Purpose: Entry point for the React frontend.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\main.tsx
 */

import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import { AppProviders } from "./providers/AppProviders";
import { bootstrapTheme } from "./theme/themeRuntime";
import "./styles.css";

bootstrapTheme();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </React.StrictMode>,
);
