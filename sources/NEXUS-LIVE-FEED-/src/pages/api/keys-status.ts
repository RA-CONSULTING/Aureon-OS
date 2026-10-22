import type { NextApiRequest, NextApiResponse } from 'next';

// This is a mock API route. In a real application, you would fetch this from a secure vault or a dedicated service.
const MOCK_VAULT_STATUS = {
  aureon: {
    present: true,
    masked: '********-****-****-****-b45b2e5a47d2',
  },
  akashic: {
    present: true,
    masked: '********-****-****-****-c3a61f8e9a1b',
  },
  prime: {
    present: true,
    masked: '********-****-****-****-a1d8b2c7e4f0',
  },
  watcher: {
    present: false,
    masked: ' ',
  },
};

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    // Simulate a network delay
    setTimeout(() => {
      res.status(200).json(MOCK_VAULT_STATUS);
    }, 1200);
  } else {
    res.setHeader('Allow', ['GET']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
