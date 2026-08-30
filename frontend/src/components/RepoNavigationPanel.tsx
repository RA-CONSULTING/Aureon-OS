import { useEffect, useMemo, useState } from "react";
import { BookOpen, CheckCircle2, ExternalLink, FileJson, GitBranch, Search, Server, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

interface RepoLink {
  label: string;
  path: string;
}

interface RepoZone {
  id: string;
  label: string;
  paths: string[];
}

interface RepoPublicContract {
  contains_secrets: boolean;
  contains_private_runtime_state: boolean;
  contains_customer_data: boolean;
  purpose: string;
}

interface RepoSitemapManifest {
  name: string;
  snapshot_date: string;
  tracked_file_count: number;
  validation_script?: string;
  validation_command?: string;
  machine_readable_source?: string;
  end_user_access_map?: string;
  frontend_navigation_tab?: string;
  organization_tree?: string;
  autonomous_frontend_manifests?: string[];
  front_doors: RepoLink[];
  zones: RepoZone[];
  public_contract: RepoPublicContract;
}

interface CapabilityRoute {
  id: string;
  label: string;
  user_action: string;
  primary_docs: string[];
  related_systems: string[];
  runtime_or_api_surface: string[];
  safety_gate: string;
}

interface AccessMapManifest {
  name: string;
  snapshot_date: string;
  source_document: string;
  capabilities: CapabilityRoute[];
}

interface CapabilityAccessMatrixSystem {
  path: string;
  category: string;
  readiness_status: string;
  access_mode: string;
  entrypoints: string[];
  public_artifacts: string[];
  validation_refs: string[];
  safety_gate: string;
}

interface CapabilityAccessMatrixRow {
  id: string;
  label: string;
  description: string;
  readiness_status: string;
  access_routes: CapabilityRoute[];
  related_systems: CapabilityAccessMatrixSystem[];
  end_user_start_points: string[];
  runtime_or_api_surfaces: string[];
  implementation_surfaces: {
    resolved_paths: string[];
    runtime_refs: string[];
    generated_refs: string[];
    code_symbol_refs: Array<{ ref: string; paths: string[] }>;
    unresolved_refs: string[];
    public_artifacts: string[];
  };
  safety_gates: string[];
}

interface CapabilityAccessMatrixManifest {
  name: string;
  snapshot_date: string;
  frontend_public_mirror: string;
  summary: {
    capability_count: number;
    routed_capability_count: number;
    system_bound_capability_count: number;
    public_artifact_capability_count: number;
    unresolved_capability_count: number;
    route_binding_count: number;
    access_route_count: number;
  };
  capabilities: CapabilityAccessMatrixRow[];
}

interface CapabilityRegistryRow {
  id: string;
  label: string;
  description: string;
  surface_refs: string[];
  resolved_paths: string[];
  runtime_refs: string[];
  generated_refs: string[];
  command_refs: string[];
  code_symbol_refs: Array<{ ref: string; paths: string[] }>;
  unresolved_refs: string[];
  system_paths: string[];
  access_route_ids: string[];
  public_artifacts: string[];
}

interface CapabilityRegistryManifest {
  name: string;
  snapshot_date: string;
  frontend_public_mirror: string;
  summary: {
    tracked_file_count: number;
    capability_count: number;
    resolved_surface_ref_count: number;
    runtime_surface_ref_count: number;
    generated_artifact_ref_count: number;
    command_surface_ref_count: number;
    code_symbol_ref_count: number;
    unresolved_surface_ref_count: number;
    access_route_count: number;
    system_count: number;
    navigation_index_entries: number;
  };
  capabilities: CapabilityRegistryRow[];
}

interface NavigationEntry {
  path: string;
  top_level: string;
  zone_id: string;
  category: string;
  role: string;
  kind: string;
  extension: string;
  capability_ids: string[];
}

interface NavigationIndexManifest {
  name: string;
  snapshot_date: string;
  tracked_file_count: number;
  entry_count: number;
  frontend_public_mirror: string;
  summary: {
    category_counts: Record<string, number>;
    zone_counts: Record<string, number>;
    capability_counts: Record<string, number>;
  };
  entries: NavigationEntry[];
}

interface OrganizationDirectory {
  path: string;
  name: string;
  parent: string;
  depth: number;
  category: string;
  role: string;
  zone_id: string;
  capability_ids: string[];
  file_count: number;
  direct_file_count: number;
  child_directory_count: number;
  child_directories: string[];
  direct_file_samples: string[];
}

interface OrganizationTreeManifest {
  name: string;
  snapshot_date: string;
  tracked_file_count: number;
  directory_count: number;
  root_file_count: number;
  max_depth: number;
  frontend_public_mirror: string;
  summary: {
    top_level_directory_count: number;
    root_file_count: number;
    category_counts: Record<string, number>;
    zone_counts: Record<string, number>;
  };
  root_files: string[];
  top_level: OrganizationDirectory[];
  directories: OrganizationDirectory[];
}

interface NavigationReadinessGate {
  id: string;
  label: string;
  status: "pass" | "warn" | "fail";
  severity: string;
  actual: unknown;
  expected: unknown;
  evidence: string[];
}

interface NavigationReadinessManifest {
  name: string;
  snapshot_date: string;
  frontend_public_mirror: string;
  summary: {
    readiness_status: "pass" | "warn" | "fail";
    tracked_file_count: number;
    directory_count: number;
    top_level_system_count: number;
    access_route_count: number;
    current_capability_count: number;
    routed_capability_count: number;
    system_mapped_capability_count: number;
    unmapped_capability_count: number;
    saas_deployment_surface_count: number;
    supabase_production_blocker_count: number;
    gate_count: number;
    passed_gate_count: number;
    failed_gate_count: number;
    warning_gate_count: number;
  };
  gates: NavigationReadinessGate[];
}

interface SystemIntegrationRow {
  path: string;
  category: string;
  tracked_files: number;
  integration_role: string;
  access_mode: string;
  readiness_status: string;
  capability_ids: string[];
  access_route_ids: string[];
  entrypoints: string[];
  public_artifacts: string[];
  validation_refs: string[];
  safety_gate: string;
}

interface SystemIntegrationMapManifest {
  name: string;
  snapshot_date: string;
  frontend_public_mirror: string;
  summary: {
    tracked_file_count: number;
    system_count: number;
    capability_count: number;
    mapped_capability_count: number;
    unmapped_capability_count: number;
    capability_system_binding_count: number;
    access_route_count: number;
    mapped_access_route_count: number;
    access_route_system_binding_count: number;
    saas_deployment_surface_count: number;
    supabase_public_blocker_count: number;
  };
  systems: SystemIntegrationRow[];
  integration_sequence: string[];
}

interface SaaSIntegrationManifest {
  name: string;
  snapshot_date: string;
  frontend_public_mirror: string;
  deployment_surfaces: Array<{ id: string; label: string; paths: string[]; mode: string; tracked: boolean }>;
  environment: {
    variable_count: number;
    sensitive_variable_count: number;
    groups: Record<string, string[]>;
  };
  supabase: {
    function_count: number;
    verify_jwt_true: number;
    verify_jwt_false: number;
    public_endpoint_review_required_count: number;
    public_endpoint_review_required: string[];
  };
  production_gates: string[];
}

interface SaaSIntegrationHandoffManifest {
  name: string;
  snapshot_date: string;
  frontend_public_mirror: string;
  summary: {
    handoff_status: string;
    readiness_status: string;
    tracked_file_count: number;
    public_manifest_count: number;
    integration_step_count: number;
    deployment_surface_count: number;
    environment_variable_name_count: number;
    environment_sensitive_name_count: number;
    current_capability_count: number;
    routed_capability_count: number;
    system_mapped_capability_count: number;
    unmapped_capability_count: number;
    supabase_function_count: number;
    supabase_verify_jwt_true: number;
    supabase_verify_jwt_false: number;
    supabase_production_blocker_count: number;
    supabase_public_medium_risk_count: number;
    supabase_jwt_review_required_count: number;
    advisory_review_item_count: number;
  };
  canonical_shape: string;
  public_assets: Array<{ id: string; path: string; purpose: string }>;
  integration_steps: Array<{ id: string; label: string; action: string; evidence: string[]; gate: string }>;
  auth_and_hardening: {
    production_status: string;
    public_medium_risk_routes: string[];
    jwt_review_required_routes: string[];
    production_gates: string[];
  };
}

interface SupabaseHardeningManifest {
  name: string;
  snapshot_date: string;
  production_status: string;
  summary: {
    function_count: number;
    verify_jwt_true: number;
    verify_jwt_false: number;
    public_high_risk_count: number;
    public_medium_risk_count: number;
    jwt_review_required_count: number;
    production_blocker_count: number;
  };
  public_high_risk_routes: string[];
  public_medium_risk_routes: string[];
  jwt_review_required_routes: string[];
  production_gates: string[];
}

interface AutonomousFrontendManifest {
  path: string;
  label: string;
  status: string;
  generated_at?: string;
  summary: Record<string, string | number | boolean | null>;
}

const REPO_BASE_URL = "https://github.com/RA-CONSULTING/Aureon-OS";
const AUTONOMOUS_MANIFEST_LABELS: Record<string, string> = {
  aureon_saas_system_inventory: "SaaS System Inventory",
  aureon_frontend_unification_plan: "Frontend Unification Plan",
  aureon_frontend_evolution_queue: "Frontend Evolution Queue",
  aureon_organism_runtime_status: "Organism Runtime Status",
  aureon_autonomous_capability_switchboard: "Autonomous Capability Switchboard",
};

function repoUrl(path: string): string {
  const cleaned = path.replace(/^\/+/, "");
  if (!cleaned) return REPO_BASE_URL;
  const mode = cleaned.endsWith("/") || !cleaned.includes(".") ? "tree" : "blob";
  return `${REPO_BASE_URL}/${mode}/main/${encodeURI(cleaned)}`;
}

function publicUrl(path: string): string {
  const file = path.split("/").pop() || path;
  return `/${file}`;
}

function manifestLabel(path: string): string {
  const file = (path.split("/").pop() || path).replace(/\.json$/, "");
  return AUTONOMOUS_MANIFEST_LABELS[file] || file.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

async function loadJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { cache: "no-store", signal });
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return (await response.json()) as T;
}

function matchesQuery(values: string[], query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return values.join(" ").toLowerCase().includes(needle);
}

function PathLink({ path }: { path: string }) {
  return (
    <a
      href={repoUrl(path)}
      target="_blank"
      rel="noreferrer"
      className="inline-flex max-w-full items-center gap-1 truncate rounded-md border border-border/60 bg-background/50 px-2 py-1 font-mono text-[11px] text-primary hover:border-primary/60"
    >
      <span className="truncate">{path}</span>
      <ExternalLink className="h-3 w-3 shrink-0" />
    </a>
  );
}

function ContractPill({ label, clear }: { label: string; clear: boolean }) {
  return (
    <Badge variant="outline" className={clear ? "border-success/40 bg-success/10 text-success" : "border-destructive/40 bg-destructive/10 text-destructive"}>
      {label}: {clear ? "clear" : "review"}
    </Badge>
  );
}

export function RepoNavigationPanel() {
  const [repoMap, setRepoMap] = useState<RepoSitemapManifest | null>(null);
  const [accessMap, setAccessMap] = useState<AccessMapManifest | null>(null);
  const [capabilityAccessMatrix, setCapabilityAccessMatrix] = useState<CapabilityAccessMatrixManifest | null>(null);
  const [capabilityRegistry, setCapabilityRegistry] = useState<CapabilityRegistryManifest | null>(null);
  const [navigationIndex, setNavigationIndex] = useState<NavigationIndexManifest | null>(null);
  const [organizationTree, setOrganizationTree] = useState<OrganizationTreeManifest | null>(null);
  const [navigationReadiness, setNavigationReadiness] = useState<NavigationReadinessManifest | null>(null);
  const [systemMap, setSystemMap] = useState<SystemIntegrationMapManifest | null>(null);
  const [saasHandoff, setSaasHandoff] = useState<SaaSIntegrationHandoffManifest | null>(null);
  const [saasManifest, setSaasManifest] = useState<SaaSIntegrationManifest | null>(null);
  const [hardeningManifest, setHardeningManifest] = useState<SupabaseHardeningManifest | null>(null);
  const [autonomousManifests, setAutonomousManifests] = useState<AutonomousFrontendManifest[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const refresh = async () => {
      try {
        const [
          repoManifest,
          accessManifest,
          capabilityAccessMatrixManifest,
          capabilityRegistryManifest,
          indexManifest,
          organizationTreeManifest,
          navigationReadinessManifest,
          systemIntegrationManifest,
          integrationHandoffManifest,
          integrationManifest,
          supabaseHardeningManifest,
        ] = await Promise.all([
          loadJson<RepoSitemapManifest>("/aureon_repo_sitemap.json", controller.signal),
          loadJson<AccessMapManifest>("/aureon_end_user_access_map.json", controller.signal),
          loadJson<CapabilityAccessMatrixManifest>("/aureon_capability_access_matrix.json", controller.signal),
          loadJson<CapabilityRegistryManifest>("/aureon_capability_registry.json", controller.signal),
          loadJson<NavigationIndexManifest>("/aureon_repo_navigation_index.json", controller.signal),
          loadJson<OrganizationTreeManifest>("/aureon_repo_organization_tree.json", controller.signal),
          loadJson<NavigationReadinessManifest>("/aureon_repo_navigation_readiness.json", controller.signal),
          loadJson<SystemIntegrationMapManifest>("/aureon_system_integration_map.json", controller.signal),
          loadJson<SaaSIntegrationHandoffManifest>("/aureon_saas_integration_handoff.json", controller.signal),
          loadJson<SaaSIntegrationManifest>("/aureon_saas_integration_manifest.json", controller.signal),
          loadJson<SupabaseHardeningManifest>("/aureon_supabase_hardening_manifest.json", controller.signal),
        ]);
        const mountedAutonomousManifests = await Promise.all(
          (repoManifest.autonomous_frontend_manifests || []).map(async (manifestPath) => {
            const manifest = await loadJson<Omit<AutonomousFrontendManifest, "path" | "label">>(publicUrl(manifestPath), controller.signal);
            return {
              ...manifest,
              path: manifestPath,
              label: manifestLabel(manifestPath),
            };
          }),
        );
        setRepoMap(repoManifest);
        setAccessMap(accessManifest);
        setCapabilityAccessMatrix(capabilityAccessMatrixManifest);
        setCapabilityRegistry(capabilityRegistryManifest);
        setNavigationIndex(indexManifest);
        setOrganizationTree(organizationTreeManifest);
        setNavigationReadiness(navigationReadinessManifest);
        setSystemMap(systemIntegrationManifest);
        setSaasHandoff(integrationHandoffManifest);
        setSaasManifest(integrationManifest);
        setHardeningManifest(supabaseHardeningManifest);
        setAutonomousManifests(mountedAutonomousManifests);
        setError("");
      } catch (loadError) {
        if (!controller.signal.aborted) {
          setError(loadError instanceof Error ? loadError.message : "Navigation manifests unavailable");
        }
      }
    };

    refresh();
    return () => controller.abort();
  }, []);

  const filteredZones = useMemo(() => {
    const zones = repoMap?.zones || [];
    return zones.filter((zone) => matchesQuery([zone.label, zone.id, ...zone.paths], query));
  }, [query, repoMap]);

  const filteredCapabilities = useMemo(() => {
    const capabilities = accessMap?.capabilities || [];
    return capabilities.filter((capability) =>
      matchesQuery(
        [
          capability.label,
          capability.id,
          capability.user_action,
          capability.safety_gate,
          ...capability.primary_docs,
          ...capability.related_systems,
          ...capability.runtime_or_api_surface,
        ],
        query,
      ),
    );
  }, [accessMap, query]);

  const filteredCapabilityAccessRows = useMemo(() => {
    const capabilities = capabilityAccessMatrix?.capabilities || [];
    return capabilities
      .filter((capability) =>
        matchesQuery(
          [
            capability.id,
            capability.label,
            capability.description,
            capability.readiness_status,
            ...capability.end_user_start_points,
            ...capability.runtime_or_api_surfaces,
            ...capability.safety_gates,
            ...capability.access_routes.flatMap((route) => [
              route.id,
              route.label,
              route.user_action,
              route.safety_gate,
              ...route.primary_docs,
              ...route.related_systems,
              ...route.runtime_or_api_surface,
            ]),
            ...capability.related_systems.flatMap((system) => [
              system.path,
              system.category,
              system.readiness_status,
              system.access_mode,
              system.safety_gate,
              ...system.entrypoints,
              ...system.public_artifacts,
              ...system.validation_refs,
            ]),
          ],
          query,
        ),
      );
  }, [capabilityAccessMatrix, query]);

  const indexedEntries = navigationIndex?.entries || [];
  const filteredEntries = useMemo(() => {
    const needle = query.trim();
    const seedPrefixes = ["README.md", "docs/", "frontend/", "aureon/", "supabase/", "scripts/validation/"];
    const entries = needle
      ? indexedEntries.filter((entry) =>
          matchesQuery([entry.path, entry.top_level, entry.zone_id, entry.category, entry.role, entry.kind, entry.extension, ...entry.capability_ids], needle),
        )
      : indexedEntries.filter((entry) => seedPrefixes.some((prefix) => entry.path === prefix.replace("/", "") || entry.path.startsWith(prefix)));
    return entries.slice(0, 120);
  }, [indexedEntries, query]);

  const organizationDirectories = organizationTree?.directories || [];
  const filteredDirectories = useMemo(() => {
    const needle = query.trim();
    const entries = needle
      ? organizationDirectories.filter((directory) =>
          matchesQuery(
            [
              directory.path,
              directory.name,
              directory.parent,
              directory.category,
              directory.role,
              directory.zone_id,
              ...directory.capability_ids,
              ...directory.direct_file_samples,
            ],
            needle,
          ),
        )
      : organizationDirectories.filter((directory) => directory.depth <= 2);
    return entries.sort((left, right) => right.file_count - left.file_count).slice(0, 30);
  }, [organizationDirectories, query]);

  const filteredReadinessGates = useMemo(() => {
    const gates = navigationReadiness?.gates || [];
    return gates
      .filter((gate) =>
        matchesQuery(
          [
            gate.id,
            gate.label,
            gate.status,
            gate.severity,
            JSON.stringify(gate.actual),
            JSON.stringify(gate.expected),
            ...gate.evidence,
          ],
          query,
        ),
      )
      .sort((left, right) => {
        const priority = { fail: 0, warn: 1, pass: 2 };
        return priority[left.status] - priority[right.status] || left.id.localeCompare(right.id);
      });
  }, [navigationReadiness, query]);

  const topCategories = useMemo(() => {
    return Object.entries(navigationIndex?.summary?.category_counts || {})
      .sort((left, right) => right[1] - left[1])
      .slice(0, 8);
  }, [navigationIndex]);

  const envGroups = useMemo(() => {
    return Object.entries(saasManifest?.environment?.groups || {})
      .sort((left, right) => right[1].length - left[1].length)
      .slice(0, 6);
  }, [saasManifest]);

  const filteredSystemRows = useMemo(() => {
    return [...(systemMap?.systems || [])]
      .filter((system) =>
        matchesQuery(
          [
            system.path,
            system.category,
            system.integration_role,
            system.readiness_status,
            system.access_mode,
            system.safety_gate,
            ...system.capability_ids,
            ...system.access_route_ids,
            ...system.entrypoints,
            ...system.public_artifacts,
            ...system.validation_refs,
          ],
          query,
        ),
      )
      .sort((left, right) => right.tracked_files - left.tracked_files);
  }, [systemMap, query]);

  const filteredAutonomousManifests = useMemo(() => {
    return autonomousManifests.filter((manifest) =>
      matchesQuery(
        [
          manifest.label,
          manifest.path,
          manifest.status,
          ...Object.entries(manifest.summary || {}).map(([key, value]) => `${key} ${String(value)}`),
        ],
        query,
      ),
    );
  }, [autonomousManifests, query]);

  const filteredCurrentCapabilities = useMemo(() => {
    const capabilities = capabilityRegistry?.capabilities || [];
    return capabilities
      .filter((capability) =>
        matchesQuery(
          [
            capability.label,
            capability.description,
            ...capability.surface_refs,
            ...capability.resolved_paths,
            ...capability.runtime_refs,
            ...capability.generated_refs,
            ...capability.command_refs,
            ...capability.code_symbol_refs.flatMap((symbol) => [symbol.ref, ...symbol.paths]),
            ...capability.unresolved_refs,
            ...capability.system_paths,
            ...capability.access_route_ids,
          ],
          query,
        ),
      );
  }, [capabilityRegistry, query]);

  const contract = repoMap?.public_contract;

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[1fr_0.75fr]">
        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <GitBranch className="h-5 w-5 text-primary" />
              Repository Map
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
              <div className="rounded-md border border-border/50 bg-background/50 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Tracked files</div>
                <div className="mt-1 text-2xl font-semibold">{(repoMap?.tracked_file_count || 0).toLocaleString()}</div>
              </div>
              <div className="rounded-md border border-border/50 bg-background/50 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Indexed paths</div>
                <div className="mt-1 text-2xl font-semibold">{(navigationIndex?.entry_count || 0).toLocaleString()}</div>
              </div>
              <div className="rounded-md border border-border/50 bg-background/50 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Directories</div>
                <div className="mt-1 text-2xl font-semibold">{(organizationTree?.directory_count || 0).toLocaleString()}</div>
              </div>
              <div className="rounded-md border border-border/50 bg-background/50 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Routed capabilities</div>
                <div className="mt-1 text-2xl font-semibold">
                  {(capabilityAccessMatrix?.summary?.routed_capability_count || capabilityRegistry?.summary?.capability_count || 0).toLocaleString()}
                </div>
              </div>
              <div className="rounded-md border border-border/50 bg-background/50 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Systems mapped</div>
                <div className="mt-1 text-2xl font-semibold">{(systemMap?.summary?.system_count || 0).toLocaleString()}</div>
              </div>
              <div className="rounded-md border border-border/50 bg-background/50 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Env names</div>
                <div className="mt-1 text-2xl font-semibold">{(saasManifest?.environment?.variable_count || 0).toLocaleString()}</div>
              </div>
              <div className="rounded-md border border-border/50 bg-background/50 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Public review</div>
                <div className="mt-1 text-2xl font-semibold">{(saasManifest?.supabase?.public_endpoint_review_required_count || 0).toLocaleString()}</div>
              </div>
            </div>

            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Filter capabilities, docs, systems, or gates"
                className="pl-9"
              />
            </div>

            {error ? (
              <div className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning">{error}</div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <ShieldCheck className="h-5 w-5 text-success" />
              Public Contract
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <ContractPill label="secrets" clear={!contract?.contains_secrets} />
              <ContractPill label="runtime state" clear={!contract?.contains_private_runtime_state} />
              <ContractPill label="customer data" clear={!contract?.contains_customer_data} />
            </div>
            <div className="grid gap-2 text-xs">
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href="/aureon_repo_sitemap.json" target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_repo_sitemap.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href="/aureon_end_user_access_map.json" target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_end_user_access_map.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href="/aureon_capability_access_matrix.json" target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_capability_access_matrix.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_capability_registry.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_capability_registry.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_repo_navigation_index.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_repo_navigation_index.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_repo_organization_tree.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_repo_organization_tree.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_repo_navigation_readiness.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_repo_navigation_readiness.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_repo_navigation_completion_audit.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_repo_navigation_completion_audit.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_system_integration_map.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_system_integration_map.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_saas_integration_manifest.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_saas_integration_manifest.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_saas_integration_handoff.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_saas_integration_handoff.json
              </a>
              <a className="inline-flex items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_supabase_hardening_manifest.json")} target="_blank" rel="noreferrer">
                <FileJson className="h-4 w-4" />
                /aureon_supabase_hardening_manifest.json
              </a>
              {filteredAutonomousManifests.map((manifest) => (
                <a
                  key={manifest.path}
                  className="inline-flex min-w-0 items-center gap-2 text-primary hover:text-primary"
                  href={publicUrl(manifest.path)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <FileJson className="h-4 w-4 shrink-0" />
                  <span className="truncate">{publicUrl(manifest.path)}</span>
                </a>
              ))}
              {repoMap?.validation_command ? (
                <div className="mt-1 rounded-md border border-border/50 bg-background/50 px-3 py-2 font-mono text-[11px] text-muted-foreground">
                  {repoMap.validation_command}
                </div>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/90">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <ShieldCheck className="h-5 w-5 text-success" />
            Navigation Readiness Audit
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Status</div>
              <div className="mt-1 text-2xl font-semibold uppercase">{navigationReadiness?.summary?.readiness_status || "pending"}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Gates passed</div>
              <div className="mt-1 text-2xl font-semibold">{(navigationReadiness?.summary?.passed_gate_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Warnings</div>
              <div className="mt-1 text-2xl font-semibold">{(navigationReadiness?.summary?.warning_gate_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Failed gates</div>
              <div className="mt-1 text-2xl font-semibold">{(navigationReadiness?.summary?.failed_gate_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Mapped capabilities</div>
              <div className="mt-1 text-2xl font-semibold">{(navigationReadiness?.summary?.system_mapped_capability_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">SaaS blockers</div>
              <div className="mt-1 text-2xl font-semibold">{(navigationReadiness?.summary?.supabase_production_blocker_count || 0).toLocaleString()}</div>
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            {filteredReadinessGates.map((gate) => (
              <div key={gate.id} className="rounded-md border border-border/50 bg-background/45 p-3">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="font-medium">{gate.label}</div>
                    <div className="mt-1 font-mono text-[10px] text-muted-foreground">{gate.id}</div>
                  </div>
                  <Badge
                    variant="outline"
                    className={
                      gate.status === "pass"
                        ? "w-fit border-success/30 bg-success/10 text-success"
                        : gate.status === "warn"
                          ? "w-fit border-warning/30 bg-warning/10 text-warning"
                          : "w-fit border-destructive/30 bg-destructive/10 text-destructive"
                    }
                  >
                    {gate.status}
                  </Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {gate.evidence.map((path) => (
                    <PathLink key={`${gate.id}-${path}`} path={path} />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="text-xs text-muted-foreground">
            Showing {filteredReadinessGates.length.toLocaleString()} of {(navigationReadiness?.summary?.gate_count || 0).toLocaleString()} readiness gates, with all matching evidence links.
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/90">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BookOpen className="h-5 w-5 text-success" />
            Capability Route Matrix
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Routed capabilities</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityAccessMatrix?.summary?.routed_capability_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Route bindings</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityAccessMatrix?.summary?.route_binding_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">System bound</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityAccessMatrix?.summary?.system_bound_capability_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Public artifacts</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityAccessMatrix?.summary?.public_artifact_capability_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Review needed</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityAccessMatrix?.summary?.unresolved_capability_count || 0).toLocaleString()}</div>
            </div>
          </div>

          <ScrollArea className="h-[640px] pr-3">
            <div className="grid gap-3 lg:grid-cols-2">
              {filteredCapabilityAccessRows.map((capability) => (
                <div key={capability.id} className="rounded-md border border-border/50 bg-background/45 p-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <div className="font-medium">{capability.label}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{capability.description}</div>
                    </div>
                    <Badge variant="outline" className="w-fit max-w-full whitespace-normal border-success/30 bg-success/10 text-[10px] leading-snug text-success">
                      {capability.readiness_status}
                    </Badge>
                  </div>
                  <div className="mt-3 space-y-2">
                    {capability.access_routes.map((route) => (
                      <div key={`${capability.id}-route-${route.id}`} className="rounded-md border border-border/40 bg-background/40 p-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                          <div className="text-sm font-medium">{route.label}</div>
                          <Badge variant="secondary" className="w-fit font-mono text-[10px]">
                            {route.id}
                          </Badge>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">{route.user_action}</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {route.runtime_or_api_surface.map((surface) => (
                            <Badge key={`${capability.id}-${route.id}-${surface}`} variant="outline" className="max-w-full whitespace-normal font-mono text-[10px] leading-snug">
                              {surface}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {capability.end_user_start_points.map((path) => (
                      <PathLink key={`${capability.id}-start-${path}`} path={path} />
                    ))}
                    {capability.related_systems.map((system) => (
                      <Badge key={`${capability.id}-system-${system.path}`} variant="secondary" className="max-w-full whitespace-normal font-mono text-[10px] leading-snug">
                        {system.path}
                      </Badge>
                    ))}
                  </div>
                  {capability.safety_gates.length ? (
                    <div className="mt-3 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
                      {capability.safety_gates.join(" / ")}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </ScrollArea>
          <div className="text-xs text-muted-foreground">
            Showing {filteredCapabilityAccessRows.length.toLocaleString()} of {(capabilityAccessMatrix?.summary?.capability_count || 0).toLocaleString()} routed capabilities, with all matching access routes, start points, systems, and gates.
          </div>
        </CardContent>
      </Card>

      {autonomousManifests.length ? (
        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <FileJson className="h-5 w-5 text-success" />
              Operational Manifests
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 lg:grid-cols-2 xl:grid-cols-5">
            {filteredAutonomousManifests.map((manifest) => (
              <a
                key={manifest.path}
                href={publicUrl(manifest.path)}
                target="_blank"
                rel="noreferrer"
                className="flex min-h-[190px] flex-col gap-3 rounded-md border border-border/50 bg-background/45 p-3 hover:border-primary/60"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-sm font-medium leading-snug">{manifest.label}</div>
                    <div className="mt-1 truncate font-mono text-[10px] text-muted-foreground">{manifest.path}</div>
                  </div>
                  <ExternalLink className="h-4 w-4 shrink-0 text-primary" />
                </div>
                <Badge variant="outline" className="w-fit max-w-full whitespace-normal border-success/30 bg-success/10 text-left text-[10px] leading-snug text-success">
                  {manifest.status}
                </Badge>
                <div className="mt-auto flex flex-wrap gap-2">
                  {Object.entries(manifest.summary || {}).slice(0, 4).map(([key, value]) => (
                    <Badge key={`${manifest.path}-${key}`} variant="secondary" className="max-w-full whitespace-normal text-[10px] leading-snug">
                      {key}: {String(value)}
                    </Badge>
                  ))}
                </div>
              </a>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Card className="border-border/60 bg-card/90">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <GitBranch className="h-5 w-5 text-primary" />
            Directory Hierarchy
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Directory nodes</div>
              <div className="mt-1 text-2xl font-semibold">{(organizationTree?.directory_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Top-level directories</div>
              <div className="mt-1 text-2xl font-semibold">{(organizationTree?.summary?.top_level_directory_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Max depth</div>
              <div className="mt-1 text-2xl font-semibold">{(organizationTree?.max_depth || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Root files</div>
              <div className="mt-1 text-2xl font-semibold">{(organizationTree?.root_file_count || 0).toLocaleString()}</div>
            </div>
          </div>
          <ScrollArea className="h-[420px] pr-3">
            <div className="grid gap-3 lg:grid-cols-2">
              {filteredDirectories.map((directory) => (
                <div key={directory.path} className="rounded-md border border-border/50 bg-background/45 p-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <PathLink path={directory.path} />
                      <div className="mt-2 text-xs text-muted-foreground">
                        Parent: {directory.parent || "[repo root]"} / depth {directory.depth}
                      </div>
                    </div>
                    <Badge variant="secondary">{directory.file_count.toLocaleString()} files</Badge>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
                    <div className="rounded-md border border-border/40 bg-background/40 px-2 py-1">{directory.category}</div>
                    <div className="rounded-md border border-border/40 bg-background/40 px-2 py-1">{directory.zone_id}</div>
                    <div className="rounded-md border border-border/40 bg-background/40 px-2 py-1">
                      {directory.child_directory_count} child dirs
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {directory.child_directories.slice(0, 4).map((childPath) => (
                      <PathLink key={`${directory.path}-${childPath}`} path={childPath} />
                    ))}
                    {directory.capability_ids.slice(0, 3).map((capabilityId) => (
                      <Badge key={`${directory.path}-${capabilityId}`} variant="outline" className="font-mono text-[10px]">
                        {capabilityId}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
          <div className="text-xs text-muted-foreground">
            Showing {filteredDirectories.length.toLocaleString()} of {(organizationTree?.directory_count || 0).toLocaleString()} directory nodes. Use search to narrow by path, zone, category, capability, or sample file.
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/90">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <CheckCircle2 className="h-5 w-5 text-success" />
            SaaS Integration Handoff
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Status</div>
              <div className="mt-1 text-xl font-semibold uppercase">{saasHandoff?.summary?.handoff_status || "pending"}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Public manifests</div>
              <div className="mt-1 text-xl font-semibold">{(saasHandoff?.summary?.public_manifest_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Steps</div>
              <div className="mt-1 text-xl font-semibold">{(saasHandoff?.summary?.integration_step_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Env names</div>
              <div className="mt-1 text-xl font-semibold">{(saasHandoff?.summary?.environment_variable_name_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Supabase blockers</div>
              <div className="mt-1 text-xl font-semibold">{(saasHandoff?.summary?.supabase_production_blocker_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Advisory items</div>
              <div className="mt-1 text-xl font-semibold">{(saasHandoff?.summary?.advisory_review_item_count || 0).toLocaleString()}</div>
            </div>
          </div>
          <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
            {(saasHandoff?.integration_steps || []).map((step) => (
              <div key={step.id} className="rounded-md border border-border/50 bg-background/45 p-3">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="font-medium">{step.label}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{step.action}</div>
                  </div>
                  <Badge variant="outline" className="w-fit max-w-full whitespace-normal border-success/30 bg-success/10 text-[10px] leading-snug text-success">
                    {step.id}
                  </Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {step.evidence.slice(0, 4).map((path) => (
                    <PathLink key={`${step.id}-${path}`} path={path} />
                  ))}
                </div>
                <div className="mt-3 rounded-md border border-border/40 bg-background/40 px-3 py-2 text-xs text-muted-foreground">
                  {step.gate}
                </div>
              </div>
            ))}
          </div>
          <a className="inline-flex max-w-full items-center gap-2 text-primary hover:text-primary" href={publicUrl("frontend/public/aureon_saas_integration_handoff.json")} target="_blank" rel="noreferrer">
            <FileJson className="h-4 w-4 shrink-0" />
            <span className="truncate">/aureon_saas_integration_handoff.json</span>
          </a>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Server className="h-5 w-5 text-success" />
              SaaS Integration Contract
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-border/50 bg-background/45 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Supabase functions</div>
                <div className="mt-1 text-xl font-semibold">{(saasManifest?.supabase?.function_count || 0).toLocaleString()}</div>
              </div>
              <div className="rounded-md border border-border/50 bg-background/45 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">JWT gated</div>
                <div className="mt-1 text-xl font-semibold">{(saasManifest?.supabase?.verify_jwt_true || 0).toLocaleString()}</div>
              </div>
              <div className="rounded-md border border-border/50 bg-background/45 p-3">
                <div className="text-[11px] uppercase text-muted-foreground">Public edge</div>
                <div className="mt-1 text-xl font-semibold">{(saasManifest?.supabase?.verify_jwt_false || 0).toLocaleString()}</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {(saasManifest?.deployment_surfaces || []).map((surface) => (
                <Badge key={surface.id} variant="outline" className={surface.tracked ? "border-success/30 bg-success/10 text-success" : "border-warning/30 bg-warning/10 text-warning"}>
                  {surface.label}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <ShieldCheck className="h-5 w-5 text-warning" />
              Integration Gates
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-2">
              <div className="text-[11px] uppercase text-muted-foreground">Environment groups</div>
              {envGroups.map(([group, names]) => (
                <div key={group} className="flex items-center justify-between rounded-md border border-border/50 bg-background/45 px-3 py-2 text-sm">
                  <span>{group}</span>
                  <Badge variant="secondary">{names.length}</Badge>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <div className="text-[11px] uppercase text-muted-foreground">Public endpoint review</div>
              {(saasManifest?.supabase?.public_endpoint_review_required || []).slice(0, 8).map((endpoint) => (
                <div key={endpoint} className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 font-mono text-xs text-warning">
                  {endpoint}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/90">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BookOpen className="h-5 w-5 text-primary" />
            Current Capability Registry
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Current capabilities</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityRegistry?.summary?.capability_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Resolved surfaces</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityRegistry?.summary?.resolved_surface_ref_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Runtime refs</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityRegistry?.summary?.runtime_surface_ref_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Generated refs</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityRegistry?.summary?.generated_artifact_ref_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Review refs</div>
              <div className="mt-1 text-2xl font-semibold">{(capabilityRegistry?.summary?.unresolved_surface_ref_count || 0).toLocaleString()}</div>
            </div>
          </div>

          <ScrollArea className="h-[620px] pr-3">
            <div className="grid gap-3 lg:grid-cols-2">
              {filteredCurrentCapabilities.map((capability) => (
                <div key={capability.id} className="rounded-md border border-border/50 bg-background/45 p-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="font-medium">{capability.label}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{capability.description}</div>
                    </div>
                    <Badge variant="outline" className="w-fit max-w-full whitespace-normal font-mono text-[10px] leading-snug">
                      {capability.access_route_ids.join(", ")}
                    </Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {capability.resolved_paths.map((path) => (
                      <PathLink key={`${capability.id}-path-${path}`} path={path} />
                    ))}
                    {capability.runtime_refs.map((ref) => (
                      <Badge key={`${capability.id}-runtime-${ref}`} variant="secondary" className="max-w-full whitespace-normal font-mono text-[10px] leading-snug">
                        {ref}
                      </Badge>
                    ))}
                    {capability.generated_refs.map((ref) => (
                      <Badge key={`${capability.id}-generated-${ref}`} variant="outline" className="max-w-full whitespace-normal border-success/30 bg-success/10 font-mono text-[10px] leading-snug text-success">
                        {ref}
                      </Badge>
                    ))}
                    {capability.code_symbol_refs.map((symbol) => (
                      <Badge key={`${capability.id}-symbol-${symbol.ref}`} variant="outline" className="max-w-full whitespace-normal border-primary/30 bg-primary/10 font-mono text-[10px] leading-snug text-primary">
                        {symbol.ref}
                      </Badge>
                    ))}
                  </div>
                  {capability.unresolved_refs.length ? (
                    <div className="mt-3 text-xs text-warning">
                      Review refs: {capability.unresolved_refs.join(", ")}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </ScrollArea>
          <div className="text-xs text-muted-foreground">
            Showing {filteredCurrentCapabilities.length.toLocaleString()} of {(capabilityRegistry?.summary?.capability_count || 0).toLocaleString()} current capabilities, with all matching access-route IDs and resolved surface references.
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/90">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Server className="h-5 w-5 text-primary" />
            System Integration Matrix
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Mapped systems</div>
              <div className="mt-1 text-2xl font-semibold">{(systemMap?.summary?.system_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Current capabilities</div>
              <div className="mt-1 text-2xl font-semibold">{(systemMap?.summary?.mapped_capability_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">System links</div>
              <div className="mt-1 text-2xl font-semibold">{(systemMap?.summary?.capability_system_binding_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Access routes</div>
              <div className="mt-1 text-2xl font-semibold">{(systemMap?.summary?.mapped_access_route_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">SaaS surfaces</div>
              <div className="mt-1 text-2xl font-semibold">{(systemMap?.summary?.saas_deployment_surface_count || 0).toLocaleString()}</div>
            </div>
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Supabase blockers</div>
              <div className="mt-1 text-2xl font-semibold">{(systemMap?.summary?.supabase_public_blocker_count || 0).toLocaleString()}</div>
            </div>
          </div>

          <ScrollArea className="h-[620px] pr-3">
            <div className="grid gap-3 lg:grid-cols-2">
              {filteredSystemRows.map((system) => (
                <div key={system.path} className="rounded-md border border-border/50 bg-background/45 p-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <PathLink path={system.path} />
                      <div className="mt-2 text-sm text-muted-foreground">{system.integration_role}</div>
                    </div>
                    <Badge variant="secondary">{system.tracked_files.toLocaleString()}</Badge>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                    <div className="rounded-md border border-border/40 bg-background/40 px-2 py-1">{system.readiness_status}</div>
                    <div className="rounded-md border border-border/40 bg-background/40 px-2 py-1">{system.access_mode}</div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {system.capability_ids.map((capabilityId) => (
                      <Badge key={`${system.path}-${capabilityId}`} variant="outline" className="font-mono text-[10px]">
                        {capabilityId}
                      </Badge>
                    ))}
                    {system.access_route_ids.map((routeId) => (
                      <Badge key={`${system.path}-route-${routeId}`} variant="secondary" className="font-mono text-[10px]">
                        {routeId}
                      </Badge>
                    ))}
                  </div>
                  <div className="mt-3 text-xs text-muted-foreground">{system.safety_gate}</div>
                </div>
              ))}
            </div>
          </ScrollArea>
          <div className="text-xs text-muted-foreground">
            Showing {filteredSystemRows.length.toLocaleString()} of {(systemMap?.summary?.system_count || 0).toLocaleString()} mapped systems, with all matching capability IDs and access-route IDs.
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/90">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <ShieldCheck className="h-5 w-5 text-warning" />
            Supabase Hardening Review
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3">
              <div className="text-[11px] uppercase text-destructive/80">Production blockers</div>
              <div className="mt-1 text-2xl font-semibold text-destructive">
                {(hardeningManifest?.summary?.production_blocker_count || 0).toLocaleString()}
              </div>
            </div>
            <div className="rounded-md border border-warning/30 bg-warning/10 p-3">
              <div className="text-[11px] uppercase text-warning/80">High-risk public</div>
              <div className="mt-1 text-2xl font-semibold text-warning">
                {(hardeningManifest?.summary?.public_high_risk_count || 0).toLocaleString()}
              </div>
            </div>
            <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
              <div className="text-[11px] uppercase text-primary/80">Medium public</div>
              <div className="mt-1 text-2xl font-semibold text-primary">
                {(hardeningManifest?.summary?.public_medium_risk_count || 0).toLocaleString()}
              </div>
            </div>
            <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
              <div className="text-[11px] uppercase text-primary/80">JWT review</div>
              <div className="mt-1 text-2xl font-semibold text-primary">
                {(hardeningManifest?.summary?.jwt_review_required_count || 0).toLocaleString()}
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-md border border-border/50 bg-background/45 p-3">
              <div className="text-[11px] uppercase text-muted-foreground">Production status</div>
              <div className="mt-2 font-mono text-xs text-warning">
                {hardeningManifest?.production_status || "pending"}
              </div>
              <div className="mt-3 text-xs text-muted-foreground">
                Generated from Supabase function auth settings and source presence. High-risk public routes must be gated or proven anonymous-safe before hosted production.
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-[11px] uppercase text-muted-foreground">High-risk public routes</div>
              <div className="grid gap-2 sm:grid-cols-2">
                {(hardeningManifest?.public_high_risk_routes || []).map((route) => (
                  <div key={route} className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 font-mono text-xs text-destructive">
                    {route}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <FileJson className="h-5 w-5 text-primary" />
              Index Categories
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {topCategories.map(([category, count]) => (
              <div key={category} className="flex items-center justify-between rounded-md border border-border/50 bg-background/45 px-3 py-2 text-sm">
                <span className="capitalize">{category}</span>
                <Badge variant="secondary">{count.toLocaleString()}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Search className="h-5 w-5 text-primary" />
              Indexed Files
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[430px] pr-3">
              <div className="space-y-2">
                {filteredEntries.map((entry) => (
                  <div key={entry.path} className="rounded-md border border-border/50 bg-background/45 p-3">
                    <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                      <PathLink path={entry.path} />
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline" className="font-mono text-[10px]">
                          {entry.kind}
                        </Badge>
                        <Badge variant="secondary" className="font-mono text-[10px]">
                          {entry.category}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{entry.role}</span>
                      <span>/</span>
                      <span>{entry.zone_id}</span>
                      {entry.capability_ids.length ? (
                        <>
                          <span>/</span>
                          <span>{entry.capability_ids.slice(0, 4).join(", ")}</span>
                        </>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
            <div className="mt-3 text-xs text-muted-foreground">
              Showing {filteredEntries.length.toLocaleString()} of {(navigationIndex?.entry_count || 0).toLocaleString()} indexed paths. Use the search field to narrow by file, folder, category, zone, or capability ID.
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Server className="h-5 w-5 text-primary" />
              System Zones
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {filteredZones.map((zone) => (
                <div key={zone.id} className="rounded-md border border-border/50 bg-background/45 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium">{zone.label}</div>
                    <Badge variant="secondary">{zone.paths.length} paths</Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {zone.paths.map((path) => (
                      <PathLink key={`${zone.id}-${path}`} path={path} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/90">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <BookOpen className="h-5 w-5 text-primary" />
              Capability Access
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[560px] pr-3">
              <div className="space-y-3">
                {filteredCapabilities.map((capability) => (
                  <div key={capability.id} className="rounded-md border border-border/50 bg-background/45 p-3">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <div className="font-medium">{capability.label}</div>
                        <div className="mt-1 text-sm text-muted-foreground">{capability.user_action}</div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                          <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                          {capability.safety_gate}
                        </div>
                      </div>
                      <Badge variant="outline" className="w-fit font-mono text-[10px]">
                        {capability.id}
                      </Badge>
                    </div>
                    <div className="mt-3 grid gap-3 xl:grid-cols-3">
                      <div>
                        <div className="mb-2 text-[11px] uppercase text-muted-foreground">Primary docs</div>
                        <div className="flex flex-wrap gap-2">
                          {capability.primary_docs.map((path) => (
                            <PathLink key={`${capability.id}-doc-${path}`} path={path} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="mb-2 text-[11px] uppercase text-muted-foreground">Related systems</div>
                        <div className="flex flex-wrap gap-2">
                          {capability.related_systems.map((path) => (
                            <PathLink key={`${capability.id}-system-${path}`} path={path} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="mb-2 text-[11px] uppercase text-muted-foreground">Runtime/API surfaces</div>
                        <div className="flex flex-wrap gap-2">
                          {capability.runtime_or_api_surface.map((surface) =>
                            surface.startsWith("frontend/") || surface.startsWith("docs/") ? (
                              <PathLink key={`${capability.id}-runtime-${surface}`} path={surface} />
                            ) : (
                              <Badge key={`${capability.id}-runtime-${surface}`} variant="secondary" className="max-w-full whitespace-normal font-mono text-[10px] leading-snug">
                                {surface}
                              </Badge>
                            ),
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/90">
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {(repoMap?.front_doors || []).slice(0, 6).map((link) => (
              <Button key={link.path} asChild variant="outline" size="sm">
                <a href={repoUrl(link.path)} target="_blank" rel="noreferrer">
                  {link.label}
                </a>
              </Button>
            ))}
          </div>
          <div className="text-xs text-muted-foreground">
            Snapshot {repoMap?.snapshot_date || "pending"} / Access map {accessMap?.snapshot_date || "pending"}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
