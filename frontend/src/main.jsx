import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App.jsx";
import MetaHubPage from "./pages/MetaHubPage.jsx";
import MapsHubPage from "./pages/MapsHubPage.jsx";
import CamoHubPage from "./pages/CamoHubPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/meta-hub" element={<MetaHubPage />} />
        <Route path="/maps-hub" element={<MapsHubPage />} />
        <Route path="/camo-hub" element={<CamoHubPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
