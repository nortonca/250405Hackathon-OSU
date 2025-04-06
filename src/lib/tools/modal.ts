import { ToolDefinition } from './types';

interface ModalState {
  isOpen: boolean;
  value: string;
  resolve: ((value: string) => void) | null;
}

class ModalManager {
  private static state: ModalState = {
    isOpen: false,
    value: '',
    resolve: null
  };

  static get modalState() {
    return this.state;
  }

  static openModal(): Promise<string> {
    return new Promise((resolve) => {
      this.state = {
        isOpen: true,
        value: '',
        resolve
      };
      document.dispatchEvent(new CustomEvent('modalStateChange', { detail: this.state }));
    });
  }

  static closeModal(value?: string) {
    if (this.state.resolve) {
      this.state.resolve(value || this.state.value);
    }
    this.state = {
      isOpen: false,
      value: '',
      resolve: null
    };
    document.dispatchEvent(new CustomEvent('modalStateChange', { detail: this.state }));
  }

  static updateValue(value: string) {
    this.state.value = value;
  }
}

export const modalTools: ToolDefinition[] = [
  {
    tool: {
      type: 'function',
      function: {
        name: 'show_input_modal',
        description: 'Show a modal dialog to get input from the user',
        parameters: {
          type: 'object',
          properties: {
            prompt: {
              type: 'string',
              description: 'The prompt to show to the user in the modal'
            }
          },
          required: ['prompt']
        }
      }
    },
    execute: async (params) => {
      try {
        const userInput = await ModalManager.openModal();
        return {
          result: `User input: ${userInput}`,
          isError: false
        };
      } catch (error) {
        return {
          result: `Failed to get user input: ${error.message}`,
          isError: true
        };
      }
    }
  }
];

export { ModalManager };