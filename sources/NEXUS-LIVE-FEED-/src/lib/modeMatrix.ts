export interface ModeDefinition {
  id: string;
  triggers: string[];
  outputs: string[];
}

export interface ModeMatrix {
  version: string;
  modes: ModeDefinition[];
  safety_hooks: {
    gamma_floor: number;
    explain_all: boolean;
  };
  interfaces: {
    compiler: string;
    ethics: string;
  };
}

export const MODE_MATRIX: ModeMatrix = {
  version: "3.0",
  modes: [
    {
      id: "phase_dynamics",
      triggers: ["guardian", "anchor", "phase"],
      outputs: ["phase_diff", "synchrony_score"],
    },
    {
      id: "symbolic_memory",
      triggers: ["pattern", "correlation"],
      outputs: ["persistence", "echo_score"],
    },
    {
      id: "stability",
      triggers: ["amplitude", "bounded", "chaos"],
      outputs: ["psi_max", "divergence_flag"],
    },
    {
      id: "lev_visual",
      triggers: ["LEV", "entanglement", "memory node"],
      outputs: ["lev_regions", "connectivity"],
    },
    {
      id: "temporal_synth",
      triggers: ["trend", "compare", "evolve"],
      outputs: ["narrative_vector", "evolution_index"],
    },
  ],
  safety_hooks: {
    gamma_floor: 0.9,
    explain_all: true,
  },
  interfaces: {
    compiler: "04_Symbolic_Compiler_v2.json",
    ethics: "06_Ethics_Directives_Sigma.json",
  },
};
