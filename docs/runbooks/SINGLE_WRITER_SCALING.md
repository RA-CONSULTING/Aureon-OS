# Single-writer deployment and scaling boundary

## Current decision

Live-capable economic and operator processes remain on exactly one deployment
instance and one process copy. This is a containment boundary, not a claim that
the current runtime has high availability.

The boundary covers the active DigitalOcean app specs, Docker Compose files,
supervisord programs, systemd worker units, and the Procfile. It prevents a
deployment setting from multiplying a process that can write shared state,
consume a provider nonce, apply a rate budget, or reach an economic action.

## Classified Compose services

| Manifest | Single-writer or control surface | Read-only surface |
| --- | --- | --- |
| docker-compose.yml | trading-engine, command-center | prometheus, grafana |
| docker-compose.autonomous.yml | aureon-autonomous | none |
| deploy/docker-compose.operator.yml | aureon-operator | none |
| deploy/docker-compose.saas.yml | aureon-operator | frontend |
| production/docker-compose.yml | aureon, command-center | prometheus, grafana |

Every service in the single-writer column is pinned to deploy replicas 1.
DigitalOcean writer services are pinned to instance_count 1 with no autoscaling
block. Operator process-manager entries are explicit singletons. Other
supervisord and systemd programs use their one-process default, and the
regression test rejects any process multiplier greater than one.

Read-only classification does not itself authorize horizontal scaling. A
dashboard, proxy, or metrics service may scale only after proving that it cannot
mutate economic/operator state and that any session, cache, rate-limit, and
storage dependency is safely externalized.

## Proof required before horizontal scaling

All of the following must exist and be independently exercised before increasing
a writer instance, replica, WSGI process, supervisor numprocs, or systemd worker
count:

1. Leader election with fencing that prevents a stale leader from acting.
2. A durable, globally unique idempotency record checked at the exact provider
   action boundary.
3. Shared provider-aware rate limits, nonce coordination, caches, and state.
4. Restart, partition, failover, and duplicate-delivery tests that prove one
   economic effect.
5. Provider and deployment read-back showing the intended topology.

The repository does not currently contain that complete proof. Keep the writer
topology at one.

## Operator checks

```powershell
python -m pytest tests/test_single_writer_scaling_contract.py
```

The Procfile describes one process type but cannot encode an external platform
dyno count. Confirm one running instance in the provider control plane before a
live-capable deployment. Local static validation is not provider read-back.
