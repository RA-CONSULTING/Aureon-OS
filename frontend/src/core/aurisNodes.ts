// 9 Auris Nodes - Symbolic Taxonomy
// Each node has unique market response curves

import type { DataProvenance } from './liveDataContract';

export type AurisNode = {
  name: string;
  weight: number;
  compute: (snapshot: MarketSnapshot) => number;
};

export type MarketSnapshot = DataProvenance & {
  price: number;
  volume: number;
  volatility: number;
  momentum: number;
  spread: number;
  timestamp: number;
};

export const AurisNodes: Record<string, AurisNode> = {
  Tiger: {
    name: 'Tiger',
    weight: 1.2,
    compute: (s) => s.volatility * 0.8 + s.spread * 0.5,
  },
  Falcon: {
    name: 'Falcon',
    weight: 1.1,
    compute: (s) => Math.abs(s.momentum) * 0.7 + s.volume * 0.3,
  },
  Hummingbird: {
    name: 'Hummingbird',
    weight: 0.8,
    compute: (s) => (1 / (s.volatility + 0.01)) * 0.6,
  },
  Dolphin: {
    name: 'Dolphin',
    weight: 1.0,
    compute: (s) => Math.sin(s.momentum) * 0.5,
  },
  Deer: {
    name: 'Deer',
    weight: 0.9,
    compute: (s) => (s.volume * 0.2 + s.volatility * 0.3 + s.spread * 0.2),
  },
  Owl: {
    name: 'Owl',
    weight: 1.0,
    compute: (s) => Math.cos(s.momentum) * 0.6 + (s.momentum < 0 ? 0.3 : 0),
  },
  Panda: {
    name: 'Panda',
    weight: 0.95,
    compute: (s) => s.volume > 0.7 ? s.volume * 0.8 : 0.2,
  },
  CargoShip: {
    name: 'CargoShip',
    weight: 1.3,
    compute: (s) => s.volume > 0.8 ? s.volume * 1.2 : 0,
  },
  Clownfish: {
    name: 'Clownfish',
    weight: 0.7,
    compute: (s) => Math.abs(s.price - s.price * 0.999) * 100,
  },
};
