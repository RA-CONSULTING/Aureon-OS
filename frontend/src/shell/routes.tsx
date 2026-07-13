/**
 * The unified shell's route table — generated from the nav registry, every
 * page lazy-loaded so each surface is its own chunk.
 */

import { createBrowserRouter, Navigate } from "react-router-dom";
import ShellLayout from "./ShellLayout";
import { ALL_NAV_ITEMS } from "./nav";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <ShellLayout />,
    children: [
      ...ALL_NAV_ITEMS.map((item) => ({
        path: item.path === "/" ? "" : item.path.replace(/^\//, ""),
        index: item.path === "/",
        element: <item.Component />,
      })),
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
