require("dotenv").config();
const express = require("express");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;

// Serve env config as a JS file so frontend can read it
app.get("/env.js", (_req, res) => {
  res.type("application/javascript");
  res.send('var API_BASE = "' + (process.env.API_BASE_URL || "http://localhost:80/api") + '";');
});

app.use(express.static(path.join(__dirname)));

app.get("*", (_req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

app.listen(PORT, () => {
  console.log(`Frontend running at http://localhost:${PORT}`);
});
