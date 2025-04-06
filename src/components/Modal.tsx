import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { ModalManager } from '../lib/tools/modal';

export function Modal() {
  const [isOpen, setIsOpen] = useState(false);
  const [value, setValue] = useState('');

  useEffect(() => {
    const handleModalStateChange = (event: CustomEvent<{ isOpen: boolean; value: string }>) => {
      setIsOpen(event.detail.isOpen);
      setValue(event.detail.value);
    };

    document.addEventListener('modalStateChange', handleModalStateChange as EventListener);
    return () => {
      document.removeEventListener('modalStateChange', handleModalStateChange as EventListener);
    };
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    ModalManager.closeModal(value);
  };

  const handleClose = () => {
    ModalManager.closeModal('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-lg font-semibold">Input Required</h2>
          <button
            onClick={handleClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4">
          <input
            type="text"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              ModalManager.updateValue(e.target.value);
            }}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            placeholder="Enter your response..."
            autoFocus
          />
          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Submit
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}