import { ToolDefinition } from './types';

export const weatherTools: ToolDefinition[] = [
  {
    tool: {
      type: 'function',
      function: {
        name: 'get_current_weather',
        description: 'Get the current weather in a given location',
        parameters: {
          type: 'object',
          properties: {
            location: {
              type: 'string',
              description: 'The city and state, e.g. San Francisco, CA'
            },
            unit: {
              type: 'string',
              enum: ['celsius', 'fahrenheit']
            }
          },
          required: ['location']
        }
      }
    },
    execute: async (params) => {
      try {
        const temp = Math.floor(Math.random() * 30) + 10;
        const unit = params.unit || 'fahrenheit';
        const conditions = ['sunny', 'cloudy', 'rainy', 'partly cloudy'][Math.floor(Math.random() * 4)];
        const unitSymbol = unit === 'celsius' ? 'C' : 'F';
        
        return {
          result: `The current weather in ${params.location} is ${temp}°${unitSymbol} and ${conditions}`,
          isError: false
        };
      } catch (error) {
        return {
          result: `Failed to get weather: ${error.message}`,
          isError: true
        };
      }
    }
  }
];