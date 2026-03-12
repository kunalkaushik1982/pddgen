/**
 * Purpose: Entry point for the React frontend.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\main.tsx
 */

import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
