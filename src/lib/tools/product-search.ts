import { ToolDefinition } from './types';

interface ProductData {
  name: string;
  sku: string;
  category: string;
  price: string;
  stock: number;
  description: string;
}

const productDatabase: ProductData[] = [
  {
    name: "Spring Celebration Bouquet",
    sku: "SPR-CELEB-01",
    category: "Bouquets > Seasonal",
    price: "$65.99",
    stock: 25,
    description: "Vibrant arrangement featuring fresh tulips, daffodils, and cherry blossoms. Perfect for celebrating spring occasions."
  },
  {
    name: "Mother's Day Special Arrangement",
    sku: "MTH-SPEC-02",
    category: "Bouquets > Special Occasions",
    price: "$89.99",
    stock: 40,
    description: "Luxurious arrangement of pink roses, white lilies, and purple orchids with decorative ribbon and personalized card."
  },
  {
    name: "Classic Red Rose Bouquet",
    sku: "ROSE-RED-12",
    category: "Bouquets > Roses",
    price: "$49.99",
    stock: 50,
    description: "One dozen premium long-stem red roses with baby's breath and elegant wrapping. A timeless romantic gesture."
  },
  {
    name: "Succulent Garden",
    sku: "SUCC-GDN-01",
    category: "Plants > Indoor",
    price: "$35.99",
    stock: 15,
    description: "Artfully arranged collection of hardy succulents in a modern ceramic planter. Low-maintenance and long-lasting."
  },
  {
    name: "Wedding Collection Package",
    sku: "WED-PKG-LUX",
    category: "Events > Wedding",
    price: "$599.99",
    stock: 5,
    description: "Complete wedding flower package including bridal bouquet, 4 bridesmaid bouquets, 8 centerpieces, and ceremony decorations."
  },
  {
    name: "Monthly Flower Subscription - Premium",
    sku: "SUB-MTH-PRM",
    category: "Subscriptions",
    price: "$75.00/month",
    stock: 100,
    description: "Monthly delivery of premium seasonal flowers. Each arrangement uniquely designed by our expert florists."
  },
  {
    name: "Sympathy Peace Lily Plant",
    sku: "PLT-PEACE-01",
    category: "Plants > Sympathy",
    price: "$45.99",
    stock: 20,
    description: "Elegant peace lily plant in a ceramic pot. A thoughtful gesture of comfort and remembrance."
  },
  {
    name: "Birthday Surprise Bouquet",
    sku: "BDAY-SURP-01",
    category: "Bouquets > Birthday",
    price: "$55.99",
    stock: 30,
    description: "Cheerful mix of gerbera daisies, sunflowers, and colorful seasonal blooms with birthday ribbon and balloon."
  },
  {
    name: "Tropical Paradise Arrangement",
    sku: "TROP-PAR-01",
    category: "Bouquets > Specialty",
    price: "$79.99",
    stock: 15,
    description: "Exotic arrangement featuring bird of paradise, tropical flowers, and palm fronds in a bamboo-inspired vase."
  },
  {
    name: "DIY Flower Arranging Kit",
    sku: "DIY-KIT-BEG",
    category: "Accessories > DIY",
    price: "$49.99",
    stock: 25,
    description: "Complete kit with seasonal flowers, vase, flower food, and arrangement guide. Perfect for beginners."
  }
];

export const productSearchTools: ToolDefinition[] = [
  {
    tool: {
      type: 'function',
      function: {
        name: 'product_search',
        description: 'Search for product information in the flower shop catalog',
        parameters: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'The natural language query about products (e.g., "Show me bouquets under $70", "What wedding packages do you have?", "How many types of plants are in stock?")'
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
                      text: productDatabase.map(product => 
                        `Name: ${product.name}  \n` +
                        `SKU: ${product.sku}  \n` +
                        `Category: ${product.category}  \n` +
                        `Price: ${product.price}  \n` +
                        `Stock: ${product.stock} units  \n` +
                        `Description: ${product.description}\n\n---\n`
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
                  text: "You are a flower shop product search assistant that provides accurate information about available flowers, plants, and arrangements. Your responses should be clear, direct, and include specific details about products including names, prices, stock levels, and key features. Format all prices with dollar signs and group related products when listing multiple items. Never say 'I can help you' or similar phrases - just provide the product information directly. If no products match the query, clearly state that no matching products were found."
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
            result: "No products found matching your query.",
            isError: false
          };
        }

        return {
          result: data.candidates[0].content.parts[0].text.trim(),
          isError: false
        };
      } catch (error) {
        console.error('Product search error:', error);
        return {
          result: `Failed to search products: ${error.message}`,
          isError: true
        };
      }
    }
  }
];