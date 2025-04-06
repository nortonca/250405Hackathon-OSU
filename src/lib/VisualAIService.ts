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
  name?: string; // Added name property for function messages
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

  static async getResponse(text: string, imageData: string | null = null): Promise<string> {
    try {
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
      try {
        result = await this.makeGroqRequest(this.conversationHistory);
      } catch (error) {
        console.error('Initial Groq API call failed:', error);
        // If the error is due to tool calls, try again without tools
        if (error.message.includes('400')) {
          console.log('Retrying without tools...');
          result = await this.makeGroqRequest(this.conversationHistory, false);
        } else {
          throw error;
        }
      }

      let aiResponse = result.choices[0].message.content;

      // Handle tool calls if present
      if (result.choices[0].message.tool_calls) {
        const toolCalls = result.choices[0].message.tool_calls;
        
        try {
          // Execute tool calls sequentially
          for (const toolCall of toolCalls) {
            // Add assistant's intention to use tool
            this.conversationHistory.push({
              role: 'assistant',
              content: `Let me check ${toolCall.function.name}...`
            });

            // Execute the tool
            const toolResult = await toolRegistry.executeToolCall(toolCall);

            // Add tool result to conversation with the required name property
            this.conversationHistory.push({
              role: 'function',
              name: toolCall.function.name, // Add the tool's name
              content: toolResult.isError ? `Error: ${toolResult.result}` : toolResult.result
            });

            // Get intermediate response if needed
            if (toolResult.isError) {
              const errorResponse = await this.makeGroqRequest(this.conversationHistory, false);
              aiResponse = errorResponse.choices[0].message.content;
              break; // Stop processing more tools if there's an error
            }
          }

          // Get final response incorporating all tool results
          if (!this.conversationHistory.some(msg => msg.content.includes('Error:'))) {
            const finalResult = await this.makeGroqRequest(this.conversationHistory, false);
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
          this.conversationHistory[0], // Keep system prompt
          ...this.conversationHistory.slice(-4) // Keep last 4 exchanges
        ];
      }

      return aiResponse;
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