// Direct stdio client for checking configured MCP packages before a Codex restart.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport, getDefaultEnvironment } from "@modelcontextprotocol/sdk/client/stdio.js";
import { resolve } from "node:path";
import { mkdir, writeFile } from "node:fs/promises";

const [server, operation = "list", ...parameters] = process.argv.slice(2);
const entries = {
  context7: ["node_modules/@upstash/context7-mcp/dist/index.js"],
  playwright: ["node_modules/@playwright/mcp/cli.js", "--headless"],
  shadcn: ["node_modules/shadcn/dist/index.js", "mcp"],
};
if (!entries[server]) throw new Error("Expected context7, playwright, or shadcn.");
const env = getDefaultEnvironment();
if (server === "context7" && process.env.CONTEXT7_API_KEY) env.CONTEXT7_API_KEY = process.env.CONTEXT7_API_KEY;
const [entry, ...args] = entries[server];
const transport = new StdioClientTransport({ command: process.execPath, args: [resolve(entry), ...args], cwd: server === "shadcn" ? resolve("web") : process.cwd(), env, stderr: "inherit" });
const client = new Client({ name: "agent-bazaar-tooling", version: "0.0.0" });
try {
  await client.connect(transport);
  let result;
  if (operation === "list") {
    result = await client.listTools();
    if (parameters[0]) result.tools = result.tools.filter(tool => tool.name.includes(parameters[0]));
  } else {
    const arguments_ = Object.fromEntries(parameters.map((value) => {
      const separator = value.indexOf("=");
      if (separator < 1) throw new Error("Tool arguments must be key=value pairs.");
      return [value.slice(0, separator), value.slice(separator + 1)];
    }));
    const available = await client.listTools();
    const schema = available.tools.find((tool) => tool.name === operation)?.inputSchema;
    for (const [key, value] of Object.entries(arguments_)) {
      if (schema?.properties?.[key]?.type === "array") arguments_[key] = value.split(",");
      if (schema?.properties?.[key]?.type === "number") arguments_[key] = Number(value);
    }
    result = await client.callTool({ name: operation, arguments: arguments_ }, undefined, { timeout: 60000 });
  }
  await mkdir(".local/mcp", { recursive: true });
  const output = `.local/mcp/${server}-${operation}-${Date.now()}.json`;
  await writeFile(output, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  console.error(`Saved ${output}`);
  if (result.isError) process.exitCode = 1;
} finally {
  await client.close();
}
