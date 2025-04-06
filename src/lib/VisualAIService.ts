import { SYSTEM_PROMPT } from './constants';
import { toolRegistry } from './tools/registry';
import { ToolCall } from './tools/types';

interface Message {
  role: 'system' | 'user' | 'assistant' | 'function';
  content: string | {
    type: 'text' | 'image_url';
    text?: string;
    image_url?: {
      url: string;
    };
  }[];
  name?: string;
}

interface ToolCallResult {
  name: string;
  result: string;
  isError: boolean;
}

interface AIResponse {
  aiResponse: string;
  toolCalls?: ToolCallResult[];
}

export class VisualAIService {
  private static conversationHistory: Message[] = [
    {
      role: 'system',
      content: SYSTEM_PROMPT
    }
  ];

  private static async makeGroqRequest(messages: Message[], includeTools = true) {
    const requestBody: any = {
      messages,
      model: 'meta-llama/llama-4-scout-17b-16e-instruct',
      temperature: 0.7,
      max_completion_tokens: 1024,
      top_p: 1,
      stream: false,
      stop: null
    };

    if (includeTools) {
      requestBody.tools = toolRegistry.getAllTools();
      requestBody.tool_choice = 'auto';
    }

    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${import.meta.env.VITE_GROQ_API_KEY}`
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Groq API error (${response.status}): ${errorText}`);
    }

    return response.json();
  }

  static async getResponse(text: string, imageData: string | null = null): Promise<AIResponse> {
    try {
      // Create user message with both text and image if available
      const userMessage: Message = {
        role: 'user',
        content: imageData ? [
          {
            type: 'text',
            text: text
          },
          {
            type: 'image_url',
            image_url: {
              url: imageData
            }
          }
        ] : text
      };

      this.conversationHistory.push(userMessage);

      let result;
      let toolCallResults: ToolCallResult[] = [];
      let hasSuccessfulToolCall = false;

      try {
        result = await this.makeGroqRequest(this.conversationHistory);
      } catch (error) {
        console.error('Initial Groq API call failed:', error);
        if (error.message.includes('400')) {
          console.log('Retrying without tools...');
          result = await this.makeGroqRequest(this.conversationHistory, false);
        } else {
          throw error;
        }
      }

      let aiResponse = result.choices[0].message.content;

      if (result.choices[0].message.tool_calls) {
        const toolCalls = result.choices[0].message.tool_calls;
        
        try {
          for (const toolCall of toolCalls) {
            this.conversationHistory.push({
              role: 'assistant',
              content: `Let me check ${toolCall.function.name}...`
            });

            const toolResult = await toolRegistry.executeToolCall(toolCall);

            toolCallResults.push({
              name: toolCall.function.name,
              result: toolResult.result,
              isError: toolResult.isError
            });

            if (!toolResult.isError) {
              hasSuccessfulToolCall = true;
            }

            this.conversationHistory.push({
              role: 'function',
              name: toolCall.function.name,
              content: toolResult.isError ? `Error: ${toolResult.result}` : toolResult.result
            });
          }

          // Only get final response if we had at least one successful tool call
          if (hasSuccessfulToolCall) {
            const finalResult = await this.makeGroqRequest([
              {
                role: 'system',
                content: `${SYSTEM_PROMPT}\n\nIMPORTANT: Tool calls have just provided valid information. Use this information in your response and do NOT say you can't see or don't have the information.`
              },
              ...this.conversationHistory.slice(-3)
            ], false);
            aiResponse = finalResult.choices[0].message.content;
          }
        } catch (error) {
          console.error('Error processing tool calls:', error);
          aiResponse = "I apologize, but I encountered an error while trying to process your request. Please try again or rephrase your question.";
        }
      }

      this.conversationHistory.push({
        role: 'assistant',
        content: aiResponse
      });

      // Keep conversation history manageable
      if (this.conversationHistory.length > 10) {
        this.conversationHistory = [
          this.conversationHistory[0],
          ...this.conversationHistory.slice(-4)
        ];
      }

      return {
        aiResponse,
        toolCalls: toolCallResults.length > 0 ? toolCallResults : undefined
      };
    } catch (error) {
      console.error('Error getting AI response:', error);
      const errorMessage = error.message || 'Unknown error occurred';
      throw new Error(`Error processing request: ${errorMessage}`);
    }
  }

  static clearHistory() {
    this.conversationHistory = [this.conversationHistory[0]];
  }
}