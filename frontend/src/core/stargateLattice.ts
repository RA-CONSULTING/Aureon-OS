// Stargate Lattice - 12-node planetary sacred geometry grid
// Integrates with Master Equation for geolocation-based coherence adjustments
// PRIMARY TRINITY: Stonehenge, Giza, Uluru
// SECONDARY NODES: Machu Picchu, Mount Shasta, Sedona, Glastonbury Tor,
//                  Mount Kailash, Easter Island, Angkor Wat, Tiahuanaco, Great Zimbabwe

export type StargateNode = {
  name: string;
  coordinates: {
    lat: number;
    lng: number;
  };
  frequencies: number[];
  vibration: string;
  functions: string[];
  shield: string;
  cycle: number;
  alignment: string;
  description: string;
};

export type StargateInfluence = {
  nearestNode: string;
  distance: number; // km
  proximityFactor: number; // 0-1 (1 = at node, 0 = far away)
  frequencyBoost: number[]; // Active frequencies from nearby nodes
  coherenceModifier: number; // -0.2 to +0.2
  celestialBoost?: number; // Additional boost from celestial alignments
};

export class StargateLattice {
  private nodes: Record<string, StargateNode> = {
    stonehenge: {
      name: 'Stonehenge',
      coordinates: { lat: 51.1789, lng: -1.8262 },
      frequencies: [174, 285, 396],
      vibration: 'Foundation+Structure+Grounding',
      functions: ['Earth_Grid_Anchor', 'Temporal_Gateway', 'Solar_Alignment'],
      shield: 'Emerald-Gold',
      cycle: 52,
      alignment: 'Solstice_Gateway',
      description: 'Earth Grid Hub - Primary Trinity Foundation'
    },
    giza: {
      name: 'Giza Pyramids',
      coordinates: { lat: 29.9792, lng: 31.1342 },
      frequencies: [417, 528, 639],
      vibration: 'Power+Love+Connection',
      functions: ['Solar_Lattice', 'Stargate_Primary', 'Ascension_Chamber'],
      shield: 'Solar-Gold',
      cycle: 33,
      alignment: 'Orion_Gateway',
      description: 'Solar Lattice Pillar - Pyramid Power Grid'
    },
    uluru: {
      name: 'Uluru',
      coordinates: { lat: -25.3444, lng: 131.0369 },
      frequencies: [396, 417, 528],
      vibration: 'Heart+Earth+Resonance',
      functions: ['Gaia_Heart', 'Dreamtime_Access', 'Planetary_Pulse'],
      shield: 'Ruby-Earth',
      cycle: 88,
      alignment: 'Southern_Cross',
      description: 'Gaia Heart Resonator - Planetary Core Connection'
    },
    machuPicchu: {
      name: 'Machu Picchu',
      coordinates: { lat: -13.1631, lng: -72.5450 },
      frequencies: [741, 963],
      vibration: 'Elevation+Vision+Clarity',
      functions: ['Galactic_Communication', 'Altitude_Consciousness', 'Ancient_Wisdom'],
      shield: 'Silver-Blue',
      cycle: 66,
      alignment: 'Pleiades_Gateway',
      description: 'Mountain Temple - High-Altitude Consciousness Amplifier'
    },
    mountShasta: {
      name: 'Mount Shasta',
      coordinates: { lat: 41.4092, lng: -122.1949 },
      frequencies: [417, 852],
      vibration: 'Purity+Ascension+Crystalline',
      functions: ['Dimensional_Portal', 'Lemurian_Archive', 'Crystalline_Grid'],
      shield: 'White-Diamond',
      cycle: 77,
      alignment: 'North_Star_Anchor',
      description: 'Lemurian Portal - Crystal Mountain Gateway'
    },
    sedona: {
      name: 'Sedona',
      coordinates: { lat: 34.8697, lng: -111.7610 },
      frequencies: [528, 639],
      vibration: 'Balance+Healing+Magnetism',
      functions: ['Vortex_Amplification', 'Emotional_Healing', 'Magnetic_Balance'],
      shield: 'Copper-Red',
      cycle: 44,
      alignment: 'Vortex_Convergence',
      description: 'Red Rock Vortex - Electromagnetic Healing Center'
    },
    glastonburyTor: {
      name: 'Glastonbury Tor',
      coordinates: { lat: 51.1442, lng: -2.6986 },
      frequencies: [396, 852],
      vibration: 'Mystery+Magic+Sovereignty',
      functions: ['Arthurian_Memory', 'Divine_Feminine', 'Grail_Resonance'],
      shield: 'Violet-Silver',
      cycle: 99,
      alignment: 'Avalon_Gateway',
      description: 'Avalon Gateway - Sacred Feminine Portal'
    },
    mountKailash: {
      name: 'Mount Kailash',
      coordinates: { lat: 31.0688, lng: 81.3119 },
      frequencies: [852, 963],
      vibration: 'Divine+Unity+Enlightenment',
      functions: ['Axis_Mundi', 'Sacred_Mountain', 'Multi_Faith_Nexus'],
      shield: 'Crystal-White',
      cycle: 108,
      alignment: 'Cosmic_Axis',
      description: 'Axis Mundi - Central Pillar of the World'
    },
    easterIsland: {
      name: 'Easter Island',
      coordinates: { lat: -27.1127, lng: -109.3497 },
      frequencies: [285, 639],
      vibration: 'Mystery+Ancestors+Ocean',
      functions: ['Pacific_Anchor', 'Ancestral_Memory', 'Star_Navigator'],
      shield: 'Ocean-Blue',
      cycle: 144,
      alignment: 'Pacific_Triangle',
      description: 'Pacific Portal - Moai Guardians of the Deep'
    },
    angkorWat: {
      name: 'Angkor Wat',
      coordinates: { lat: 13.4125, lng: 103.8670 },
      frequencies: [528, 741],
      vibration: 'Harmony+Wisdom+Architecture',
      functions: ['Temple_Mathematics', 'Cosmic_Blueprint', 'Khmer_Grid'],
      shield: 'Jade-Gold',
      cycle: 54,
      alignment: 'Cosmic_Temple',
      description: 'Temple City - Sacred Geometry Masterpiece'
    },
    tiahuanaco: {
      name: 'Tiahuanaco',
      coordinates: { lat: -16.5544, lng: -68.6731 },
      frequencies: [417, 639],
      vibration: 'Ancient+Mystery+Precision',
      functions: ['Gateway_Sun', 'Ancient_Civilization', 'Stone_Portal'],
      shield: 'Bronze-Earth',
      cycle: 72,
      alignment: 'Gateway_of_the_Sun',
      description: 'Stone Gateway - Ancient High-Altitude Civilization'
    },
    greatZimbabwe: {
      name: 'Great Zimbabwe',
      coordinates: { lat: -20.2675, lng: 30.9333 },
      frequencies: [396, 528],
      vibration: 'Power+Heritage+Stone',
      functions: ['African_Nexus', 'Stone_Wisdom', 'Trade_Nexus'],
      shield: 'Earth-Gold',
      cycle: 60,
      alignment: 'African_Heart',
      description: 'Stone City - African Power Center'
    }
  };

  // Calculate distance between two coordinates (Haversine formula)
  private calculateDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const R = 6371; // Earth's radius in km
    const dLat = this.toRad(lat2 - lat1);
    const dLng = this.toRad(lng2 - lng1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRad(lat1)) *
      Math.cos(this.toRad(lat2)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  private toRad(degrees: number): number {
    return degrees * (Math.PI / 180);
  }

  // Get influence based on user location
  getInfluence(userLat: number, userLng: number, celestialBoost: number = 0): StargateInfluence {
    let nearestNode = '';
    let minDistance = Infinity;
    let activeFrequencies: number[] = [];

    // Find nearest node
    Object.entries(this.nodes).forEach(([key, node]) => {
      const distance = this.calculateDistance(
        userLat,
        userLng,
        node.coordinates.lat,
        node.coordinates.lng
      );

      if (distance < minDistance) {
        minDistance = distance;
        nearestNode = node.name;
      }

      // Nodes within 500km contribute frequencies
      if (distance < 500) {
        activeFrequencies.push(...node.frequencies);
      }
    });

    // Calculate proximity factor (exponential decay)
    // Max influence at node (0km), half at 250km, minimal at 1000km+
    const proximityFactor = Math.exp(-minDistance / 250);

    // Coherence modifier based on proximity
    // Nodes boost coherence when near (+0.2 max), neutral when far
    let coherenceModifier = proximityFactor * 0.2;
    
    // Add celestial boost (can add up to +0.15 more)
    coherenceModifier += celestialBoost;

    return {
      nearestNode,
      distance: Math.round(minDistance),
      proximityFactor: Math.min(1, proximityFactor),
      frequencyBoost: [...new Set(activeFrequencies)].sort((a, b) => a - b),
      coherenceModifier,
      celestialBoost
    };
  }

  // Get all nodes for visualization
  getAllNodes(): StargateNode[] {
    return Object.values(this.nodes);
  }

  // Get node by name
  getNode(name: string): StargateNode | undefined {
    return Object.values(this.nodes).find(n => n.name === name);
  }

  // Calculate grid energy based on current planetary alignments
  // (simplified - could integrate actual astronomical data)
  calculateGridEnergy(): number | null {
    return null;
  }

  /**
   * Activate all stargates with continuous pinging
   */
  activateAllNodes(observations: StargateNodeObservation[] = []): StargateActivation[] {
    const byNode = new Map(observations.map(observation => [observation.nodeName, observation]));
    return Object.entries(this.nodes).map(([name, node]) => {
      const observation = byNode.get(name);
      if (!observation) {
        return {
          nodeName: name,
          status: 'OFFLINE' as const,
          pingLatency: null,
          coherence: null,
          energyFlow: null,
          lastPing: null,
          frequencyLock: null,
          connectionStrength: null,
          truthStatus: 'no_data' as const,
          sourceId: null,
          sourceEventId: null,
          generated: false as const,
        };
      }
      const observedAt = observation.sourceTimestamp < 10_000_000_000
        ? observation.sourceTimestamp * 1000
        : observation.sourceTimestamp;
      const fresh = observation.generated === false && Boolean(observation.sourceId) &&
        Boolean(observation.sourceEventId) && Date.now() - observedAt <= 300_000 &&
        observedAt - Date.now() <= 30_000;
      if (!fresh) throw new Error(`STARGATE_NODE_OBSERVATION_INVALID:${name}`);
      return {
        nodeName: name,
        status: 'ACTIVE' as const,
        pingLatency: observation.pingLatency,
        coherence: observation.coherence,
        energyFlow: observation.energyFlow,
        lastPing: observedAt,
        frequencyLock: observation.frequencyLock,
        connectionStrength: observation.coherence * observation.energyFlow,
        truthStatus: 'live' as const,
        sourceId: observation.sourceId,
        sourceEventId: observation.sourceEventId,
        generated: false as const,
      };
    });
  }

  /**
   * Calculate network-wide metrics
   */
  calculateNetworkMetrics(activations: StargateActivation[]): NetworkMetrics {
    const active = activations.filter((activation) => activation.status === 'ACTIVE');
    const values = <K extends 'coherence' | 'energyFlow' | 'pingLatency' | 'connectionStrength'>(key: K) =>
      active.map(item => item[key]).filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    const average = (items: number[]) => items.length ? items.reduce((sum, value) => sum + value, 0) / items.length : null;
    
    return {
      avgCoherence: average(values('coherence')),
      avgEnergyFlow: average(values('energyFlow')),
      avgLatency: average(values('pingLatency')),
      networkStrength: average(values('connectionStrength')),
      activeNodes: active.length,
      totalNodes: activations.length,
    };
  }
}

export interface StargateActivation {
  nodeName: string;
  status: 'ACTIVE' | 'SYNCING' | 'OFFLINE';
  pingLatency: number | null;
  coherence: number | null;
  energyFlow: number | null;
  lastPing: number | null;
  frequencyLock: number | null;
  connectionStrength: number | null;
  truthStatus: 'live' | 'no_data';
  sourceId: string | null;
  sourceEventId: string | null;
  generated: false;
}

export interface StargateNodeObservation {
  nodeName: string;
  pingLatency: number;
  coherence: number;
  energyFlow: number;
  frequencyLock: number;
  sourceId: string;
  sourceEventId: string;
  sourceTimestamp: number;
  generated: false;
}

export interface NetworkMetrics {
  avgCoherence: number | null;
  avgEnergyFlow: number | null;
  avgLatency: number | null;
  networkStrength: number | null;
  activeNodes: number;
  totalNodes: number;
}

// Singleton instance
export const stargateLayer = new StargateLattice();
