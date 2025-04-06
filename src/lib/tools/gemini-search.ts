import { ToolDefinition } from './types';

export const geminiSearchTools: ToolDefinition[] = [
  {
    tool: {
      type: 'function',
      function: {
        name: 'gemini_search',
        description: 'Search for real-time information about any topic using Google Gemini AI',
        parameters: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'The search query to look up'
            }
          },
          required: ['query']
        }
      }
    },
    execute: async (params) => {
      try {
        const response = await fetch(
          `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${import.meta.env.VITE_GEMINI_API_KEY}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              contents: [
                {
                  role: 'user',
                  parts: [{ text: params.query }]
                }
              ],
              systemInstruction: {
                parts: [{
                  text: "You are an AI assistant that provides accurate, up-to-date information about any topic. Your responses should be clear, factual, and concise. Always use real-time information from reliable sources to answer queries."
                }]
              },
              generationConfig: {
                temperature: 0.7,
                topK: 40,
                topP: 0.95,
                maxOutputTokens: 1024,
              },
              tools: [{ googleSearch: {} }]
            })
          }
        );

        if (!response.ok) {
          throw new Error(`Gemini API error: ${response.status}`);
        }

        const data = await response.json();
        
        if (!data.candidates || data.candidates.length === 0) {
          return {
            result: "No results found for this query.",
            isError: false
          };
        }

        return {
          result: data.candidates[0].content.parts[0].text.trim(),
          isError: false
        };
      } catch (error) {
        console.error('Gemini search error:', error);
        return {
          result: `Failed to perform Gemini search: ${error.message}`,
          isError: true
        };
      }
    }
  }
];