import { onRequest } from "firebase-functions/v2/https";
import server from "./server.js";

export const api = onRequest(server);
