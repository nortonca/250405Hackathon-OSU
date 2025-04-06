import { ToolDefinition } from './types';

interface CustomerData {
  name: string;
  email: string;
  phone: string;
  address: string;
  product: string;
  quantity: number;
  price: string;
  paymentMethod: string;
  orderDate: string;
  deliveryStatus: string;
}

const customerDatabase: CustomerData[] = [
  {
    name: "Sarah Williams",
    email: "sarah.w@example.com",
    phone: "(415) 555-0123",
    address: "742 Rose Garden Ave, San Francisco, CA 94110",
    product: "Spring Celebration Bouquet",
    quantity: 1,
    price: "$65.99",
    paymentMethod: "Visa - **** 4521",
    orderDate: "2025-04-03",
    deliveryStatus: "Delivered"
  },
  {
    name: "David Chen",
    email: "dchen@example.com",
    phone: "(206) 555-0456",
    address: "1234 Tulip Lane, Seattle, WA 98115",
    product: "Mother's Day Special Arrangement",
    quantity: 2,
    price: "$89.99 each",
    paymentMethod: "PayPal",
    orderDate: "2025-04-02",
    deliveryStatus: "Scheduled"
  },
  {
    name: "Maria Rodriguez",
    email: "maria.r@example.com",
    phone: "(312) 555-0789",
    address: "567 Daisy Street, Chicago, IL 60651",
    product: "Monthly Flower Subscription - Premium",
    quantity: 1,
    price: "$75.00/month",
    paymentMethod: "Mastercard - **** 8765",
    orderDate: "2025-04-01",
    deliveryStatus: "Active Subscription"
  },
  {
    name: "James Thompson",
    email: "j.thompson@example.com",
    phone: "(646) 555-0321",
    address: "890 Lily Court, New York, NY 10075",
    product: "Sympathy Peace Lily Plant",
    quantity: 1,
    price: "$45.99",
    paymentMethod: "Apple Pay",
    orderDate: "2025-03-31",
    deliveryStatus: "Delivered"
  },
  {
    name: "Emily Parker",
    email: "eparker@example.com",
    phone: "(469) 555-0654",
    address: "432 Sunflower Drive, Dallas, TX 75217",
    product: "Wedding Collection Package",
    quantity: 1,
    price: "$599.99",
    paymentMethod: "Discover - **** 1234",
    orderDate: "2025-04-04",
    deliveryStatus: "Consultation Scheduled"
  }
];

export const customerDataTools: ToolDefinition[] = [
  {
    tool: {
      type: 'function',
      function: {
        name: 'customer_data_lookup',
        description: 'Query customer order information from the flower shop database',
        parameters: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'The natural language query about customer data (e.g., "What did Sarah order?", "Show me all delivered orders", "Find wedding orders")'
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
                  parts: [
                    {
                      text: customerDatabase.map(customer => 
                        `Customer Name: ${customer.name}  \n` +
                        `Email: ${customer.email}  \n` +
                        `Phone: ${customer.phone}  \n` +
                        `Address: ${customer.address}  \n` +
                        `Product: ${customer.product}  \n` +
                        `Quantity: ${customer.quantity}  \n` +
                        `Price: ${customer.price}  \n` +
                        `Payment Method: ${customer.paymentMethod}  \n` +
                        `Order Date: ${customer.orderDate}  \n` +
                        `Delivery Status: ${customer.deliveryStatus}\n\n---\n`
                      ).join('\n')
                    },
                    {
                      text: params.query
                    }
                  ]
                }
              ],
              systemInstruction: {
                parts: [{
                  text: "You are a flower shop customer service assistant that provides accurate information about customer orders. Your responses should be clear, direct, and include all relevant details about orders, delivery status, and customer information when appropriate. Never make up information beyond what's in the database."
                }]
              },
              generationConfig: {
                temperature: 0.1,
                topK: 1,
                topP: 1,
                maxOutputTokens: 1024,
              }
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
        console.error('Customer data lookup error:', error);
        return {
          result: `Failed to look up customer data: ${error.message}`,
          isError: true
        };
      }
    }
  }
];