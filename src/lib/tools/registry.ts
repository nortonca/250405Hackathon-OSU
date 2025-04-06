import { Tool, ToolCall, ToolResult, ToolDefinition } from './types';
import { geminiSearchTools } from './gemini-search';
import { modalTools } from './modal';
import { customerDataTools } from './customer-data';
import { productSearchTools } from './product-search';

class ToolRegistry {
  private tools: Map<string, ToolDefinition> = new Map();

  constructor() {
    this.registerTools([
      ...geminiSearchTools, 
      ...modalTools,
      ...customerDataTools,
      ...productSearchTools
    ]);
  }

  private registerTools(tools: ToolDefinition[]) {
    for (const tool of tools) {
      this.tools.set(tool.tool.function.name, tool);
    }
  }

  getAllTools(): Tool[] {
    return Array.from(this.tools.values()).map(def => def.tool);
  }

  async executeToolCall(toolCall: ToolCall): Promise<ToolResult> {
    try {
      const { name, arguments: args } = toolCall.function;
      const tool = this.tools.get(name);
      
      if (!tool) {
        return {
          result: `Error: Unknown tool "${name}"`,
          isError: true
        };
      }

      const params = JSON.parse(args);
      return await tool.execute(params);
    } catch (error) {
      return {
        result: `Error executing tool: ${error.message}`,
        isError: true
      };
    }
  }
}

export const toolRegistry = new ToolRegistry();