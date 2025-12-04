import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

// 禁用F5刷新页面
document.addEventListener('keydown', (e) => {
  if (e.key === 'F5') {
    e.preventDefault();
  }
});

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
