# HNC useful-throughput pilot

12 September 2026. This pilot profiles the unchanged, hash-pinned fine-grid kernel before extending the computational campaign. It does not overwrite the 16,777,216-step results or alter the author's beta=1 reference.

One node / four GPUs / four independent workers; a 20-minute ceiling (one-third node-hour). Workers use the existing task configurations 0, 31, 64 and 127, covering short and long history lengths and low and high gains. Each worker requires exactly one visible GPU and records its UUID.

Measure the unchanged kernel on the original alpha/beta grid at 1x, 2x and 4x batch size, three repetitions after warm-up, for 1,024 steps with burn-in 256. Larger batches deliberately duplicate parameter points for performance testing. They are not new initial conditions or independent scientific observations. Require bitwise matching duplicate output arrays for all reported dynamical fields before considering an expanded batch eligible. Report all timings, including failures, and compare median useful trajectory-steps per second.

Collect a separate 128-step CPU/CUDA operator profile. Instrumented durations are not used as uninstrumented throughput. Device-event sums and CPU-event sums are diagnostic aggregates, not a direct GPU-utilization percentage. Measure the current full-horizon forcing allocation separately by running one trajectory step while retaining the original 16,777,216-element forcing horizon. This includes setup and a recurrence step, so it is not described as pure forcing time.

The source currently constructs forcing for the entire horizon on every run_grid call, including resumed segments, and issues many tensor operations inside a Python time-step loop. These are implementation observations; their contribution to runtime must be measured before optimising. Any later kernel fusion, forcing change or initial-condition ensemble requires a separately versioned implementation, appropriate numerical/continuation checks and a new scientific protocol where applicable. This pilot does not itself authorise claiming that a shorter horizon validates the original long run or the full HNC theory.
