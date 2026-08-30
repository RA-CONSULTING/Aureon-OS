import { useEffect, useMemo, useState } from "react";
import { Building2, BriefcaseBusiness, ListChecks, Network, ShieldCheck, Users, Workflow } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

type JsonMap = Record<string, any>;

async function fetchJson(url: string): Promise<JsonMap> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return {};
    return await response.json();
  } catch {
    return {};
  }
}

function fmt(value: unknown): string {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toLocaleString() : String(value || "0");
}

function roleTone(role: JsonMap): "success" | "warning" | "outline" {
  if (role.status === "active_surface_mapped") return "success";
  if ((role.work_orders || []).length) return "warning";
  return "outline";
}

function departmentRoles(report: JsonMap, departmentId: string): JsonMap[] {
  const roles = Array.isArray(report.roles) ? report.roles : [];
  return roles.filter((role: JsonMap) => role.department === departmentId);
}

export function AureonAgentCompanyConsole() {
  const [report, setReport] = useState<JsonMap>({});

  const refresh = async () => {
    const payload = await fetchJson("/aureon_agent_company_bill_list.json");
    setReport(payload);
  };

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 30000);
    return () => window.clearInterval(timer);
  }, []);

  const summary = report.summary || {};
  const departments = Array.isArray(report.departments) ? report.departments : [];
  const boundaries = Array.isArray(report.authority_boundaries) ? report.authority_boundaries : [];
  const workOrders = Array.isArray(report.work_orders) ? report.work_orders : [];
  const coverage = Array.isArray(report.capability_coverage) ? report.capability_coverage : [];
  const handoffMap = Array.isArray(report.handoff_map) ? report.handoff_map : [];
  const dailyLoop = Array.isArray(report.daily_operating_loop) ? report.daily_operating_loop : [];
  const accessPolicy = report.whole_organism_access_policy || {};
  const myceliumDoctrine = report.mycelium_organisation_doctrine || {};
  const myceliumMap = Array.isArray(myceliumDoctrine.metaphor_map) ? myceliumDoctrine.metaphor_map : [];
  const myceliumPrinciples = Array.isArray(myceliumDoctrine.operating_principles) ? myceliumDoctrine.operating_principles : [];
  const bioCosmicDoctrine = report.bio_cosmic_organisation_doctrine || {};
  const bioCosmicScale = Array.isArray(bioCosmicDoctrine.scale_ladder) ? bioCosmicDoctrine.scale_ladder : [];
  const bioCosmicLaws = Array.isArray(bioCosmicDoctrine.operating_laws) ? bioCosmicDoctrine.operating_laws : [];
  const agencyModel = report.agency_operating_model || {};
  const clientJobLifecycle = Array.isArray(report.prompt_client_job_lifecycle) ? report.prompt_client_job_lifecycle : [];
  const retirementPolicy = report.subcontractor_retirement_policy || {};
  const memoryPhonebook = report.workforce_memory_phonebook || {};
  const memorySummary = memoryPhonebook.summary || {};
  const recruitmentEngine = report.recruitment_engine || {};
  const recruitmentSummary = recruitmentEngine.summary || {};
  const recruitedWorkers = Array.isArray(recruitmentEngine.recruited_workers) ? recruitmentEngine.recruited_workers : [];
  const recruitmentStages = Array.isArray(recruitmentEngine.stage_flow) ? recruitmentEngine.stage_flow : [];
  const onlineSearch = recruitmentEngine.online_skill_searches || {};
  const onlineSearches = Array.isArray(onlineSearch.searches) ? onlineSearch.searches : [];
  const topWorkOrders = useMemo(() => workOrders.slice(0, 5), [workOrders]);

  return (
    <Card className="mb-5 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Building2 className="h-4 w-4 text-primary" />
          Aureon Agent Company
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant={report.status ? "success" : "warning"}>{report.status || "waiting for company registry"}</Badge>
          <Badge variant="outline">updated {report.generated_at ? new Date(report.generated_at).toLocaleTimeString() : "pending"}</Badge>
          <Badge variant={summary.existing_gates_preserved ? "success" : "warning"}>gates {summary.existing_gates_preserved ? "preserved" : "check"}</Badge>
          <Badge variant={summary.executable_agents_created ? "warning" : "outline"}>mode {summary.registry_mode || "registry ui first"}</Badge>
        </div>

        <div className="grid gap-2 md:grid-cols-4 xl:grid-cols-8">
          <Stat icon={Users} label="roles" value={summary.role_count || 0} />
          <Stat icon={Building2} label="departments" value={summary.department_count || 0} />
          <Stat icon={BriefcaseBusiness} label="active mapped" value={summary.active_surface_role_count || 0} />
          <Stat icon={Workflow} label="work orders" value={summary.work_order_count || 0} />
          <Stat icon={ShieldCheck} label="boundaries" value={summary.authority_boundary_count || 0} />
          <Stat icon={Network} label="coverage" value={`${fmt(summary.coverage_percent)}%`} />
          <Stat icon={ListChecks} label="day plans" value={summary.roles_with_day_plan_count || 0} />
          <Stat icon={Network} label="whole access" value={summary.roles_with_whole_organism_access_count || 0} />
          <Stat icon={BriefcaseBusiness} label="agency roles" value={summary.agency_workforce_role_count || 0} />
          <Stat icon={Workflow} label="temp-ready" value={summary.subcontractor_eligible_role_count || 0} />
          <Stat icon={Users} label="recruited" value={summary.recruited_worker_count || 0} />
          <Stat icon={Network} label="online scans" value={summary.online_recruitment_search_count || 0} />
          <Stat icon={Network} label="memory packs" value={summary.sha256_memory_entry_count || 0} />
          <Stat icon={Network} label="mycelium map" value={summary.mycelium_metaphor_count || myceliumMap.length || 0} />
          <Stat icon={Network} label="bio scale" value={summary.bio_cosmic_scale_count || bioCosmicScale.length || 0} />
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-sm font-medium">Company Departments</div>
              <Badge variant="outline">CEO to cleaner</Badge>
            </div>
            <ScrollArea className="h-[420px] pr-3">
              <div className="space-y-3">
                {departments.map((department: JsonMap) => {
                  const roles = departmentRoles(report, department.id);
                  return (
                    <div key={department.id} className="rounded-md border border-border/40 bg-background/30 p-3">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="text-sm font-medium">{department.title}</div>
                          <div className="mt-1 text-xs text-muted-foreground">{department.mission}</div>
                        </div>
                        <Badge variant="outline">{roles.length} roles</Badge>
                      </div>
                      <div className="mt-3 grid gap-2 md:grid-cols-2">
                        {roles.map((role: JsonMap) => (
                          <div key={role.role_id} className="rounded border border-border/30 bg-muted/10 p-2">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="truncate text-xs font-medium">{role.title}</div>
                                <div className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">{role.mission}</div>
                              </div>
                              <Badge variant={roleTone(role)}>{String(role.authority_level || "authority").replace(/_/g, " ")}</Badge>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-1">
                              {(role.capabilities || []).slice(0, 3).map((capability: string) => (
                                <Badge key={capability} variant="outline" className="text-[10px]">
                                  {capability.replace(/_/g, " ")}
                                </Badge>
                              ))}
                            </div>
                            <div className="mt-2 space-y-1 border-t border-border/30 pt-2">
                              {(role.day_to_day || []).slice(0, 2).map((item: string, index: number) => (
                                <div key={`${role.role_id}-day-${index}`} className="line-clamp-2 text-[11px] text-muted-foreground">
                                  {item}
                                </div>
                              ))}
                              <div className="flex flex-wrap gap-1 pt-1">
                                <Badge variant="outline" className="text-[10px]">
                                  access {(role.whole_organism_access?.allowed_surfaces || []).length || 0}
                                </Badge>
                                <Badge variant="outline" className="text-[10px]">
                                  checks {(role.standing_checks || []).length}
                                </Badge>
                                <Badge variant="outline" className="text-[10px]">
                                  escalates {(role.escalation_rules || []).length}
                                </Badge>
                                <Badge variant="outline" className="text-[10px]">
                                  {String(role.workforce_lifecycle?.employment_model || "workforce").replace(/_/g, " ")}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {!departments.length ? (
                  <div className="rounded-md border border-border/40 bg-muted/10 p-4 text-sm text-muted-foreground">
                    Run python -m aureon.autonomous.aureon_agent_company_builder to publish the registry.
                  </div>
                ) : null}
              </div>
            </ScrollArea>
          </div>

          <div className="space-y-3">
            <div className="rounded-md border border-success/30 bg-success/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-success">Mycelium Organisation Ethos</div>
                <Badge variant={summary.mycelium_doctrine_ready ? "success" : "warning"}>
                  {String(myceliumDoctrine.ethos || "waiting").replace(/_/g, " ")}
                </Badge>
              </div>
              <div className="text-[11px] text-muted-foreground">{myceliumDoctrine.one_line || "Waiting for mycelium doctrine."}</div>
              <div className="mt-2 space-y-1">
                {myceliumMap.slice(0, 5).map((item: JsonMap) => (
                  <div key={item.mycelium_part} className="rounded border border-success/20 bg-background/20 px-2 py-1.5">
                    <div className="text-[11px] font-medium">
                      {String(item.mycelium_part || "").replace(/_/g, " ")} {"->"} {item.aureon_part}
                    </div>
                    <div className="mt-0.5 text-[11px] text-muted-foreground">{item.function}</div>
                  </div>
                ))}
              </div>
              <div className="mt-2 grid gap-1">
                {myceliumPrinciples.slice(0, 4).map((principle: string) => (
                  <div key={principle} className="rounded border border-success/20 bg-background/15 px-2 py-1 text-[11px] text-muted-foreground">
                    {principle}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-primary">Cells To Stars Doctrine</div>
                <Badge variant={summary.bio_cosmic_doctrine_ready ? "success" : "warning"}>
                  {String(bioCosmicDoctrine.ethos || "waiting").replace(/_/g, " ")}
                </Badge>
              </div>
              <div className="text-[11px] text-muted-foreground">{bioCosmicDoctrine.one_line || "Waiting for living-system doctrine."}</div>
              <div className="mt-2 grid gap-1">
                {bioCosmicScale.slice(0, 6).map((item: JsonMap) => (
                  <div key={item.scale} className="rounded border border-primary/20 bg-background/20 px-2 py-1.5">
                    <div className="text-[11px] font-medium">{String(item.scale || "").replace(/_/g, " ")}</div>
                    <div className="mt-0.5 text-[11px] text-muted-foreground">{item.aureon_translation}</div>
                  </div>
                ))}
              </div>
              <div className="mt-2 grid gap-1">
                {bioCosmicLaws.slice(0, 4).map((law: string) => (
                  <div key={law} className="rounded border border-primary/20 bg-background/15 px-2 py-1 text-[11px] text-muted-foreground">
                    {law}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-primary">Prompt As Client Job</div>
                <Badge variant="outline">{summary.agency_lifecycle_step_count || clientJobLifecycle.length} stages</Badge>
              </div>
              <div className="text-[11px] text-muted-foreground">{agencyModel.analogy || "Waiting for agency model."}</div>
              <div className="mt-2 space-y-2">
                {clientJobLifecycle.map((step: JsonMap) => (
                  <div key={step.step} className="rounded border border-primary/20 bg-background/25 p-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs font-medium">{String(step.step || "").replace(/_/g, " ")}</div>
                      <Badge variant="outline" className="text-[10px]">{step.owner}</Badge>
                    </div>
                    <div className="mt-1 text-[11px] text-muted-foreground">{step.action}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-primary">Recruitment Engine</div>
                <Badge variant={recruitmentEngine.status === "recruitment_ready" ? "success" : "warning"}>
                  {recruitmentEngine.status || "waiting"}
                </Badge>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                <div className="rounded border border-primary/20 bg-background/25 p-2">
                  <div className="text-xs font-medium">Search Stack</div>
                  <div className="mt-1 text-[11px] text-muted-foreground">
                    internal hits {recruitmentSummary.internal_hit_count || 0}; online {String(recruitmentSummary.online_enabled ?? false)}; status {recruitmentSummary.online_status || "not requested"}
                  </div>
                  <div className="mt-2 space-y-1">
                    {onlineSearches.slice(0, 3).map((search: JsonMap) => (
                      <div key={search.id || search.query} className="truncate text-[11px] text-muted-foreground">
                        {search.query} ({search.result_count || 0})
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded border border-primary/20 bg-background/25 p-2">
                  <div className="text-xs font-medium">Recruited Crew</div>
                  <div className="mt-1 text-[11px] text-muted-foreground">
                    {recruitedWorkers.length || 0} workers; blueprints {recruitmentSummary.agent_blueprint_count || 0}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {recruitedWorkers.slice(0, 6).map((worker: JsonMap) => (
                      <Badge key={worker.role_id} variant="outline" className="text-[10px]">
                        {worker.title}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-2 space-y-1">
                {recruitmentStages.slice(0, 4).map((stage: JsonMap) => (
                  <div key={stage.stage} className="rounded border border-primary/20 bg-background/20 px-2 py-1.5">
                    <div className="text-[11px] font-medium">{String(stage.stage || "").replace(/_/g, " ")}</div>
                    <div className="mt-0.5 text-[11px] text-muted-foreground">{stage.owner}: {stage.action}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-warning/30 bg-warning/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-warning">Hire / Retire Crews</div>
                <Badge variant={summary.temporary_staff_retirement_policy_ready ? "success" : "warning"}>
                  {summary.temporary_staff_retirement_policy_ready ? "ready" : "check"}
                </Badge>
              </div>
              <div className="space-y-1 text-[11px] text-muted-foreground">
                <div>{retirementPolicy.retire_means || "Waiting for retirement policy."}</div>
                <div>{retirementPolicy.delete_means || ""}</div>
              </div>
            </div>

            <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-primary">Memory Phonebook</div>
                <Badge variant={summary.memory_phonebook_ready ? "success" : "warning"}>
                  {memorySummary.entry_count || 0} packs
                </Badge>
              </div>
              <div className="space-y-1 text-[11px] text-muted-foreground">
                <div>sha256 addressed: {String(memorySummary.sha256_addressed ?? false)}</div>
                <div>zlib compressed: {String(memorySummary.zlib_compressed ?? false)}</div>
                <div>compression ratio: {memorySummary.compression_ratio || "pending"}</div>
              </div>
              <div className="mt-2 space-y-1">
                {(memoryPhonebook.entries || []).slice(0, 3).map((entry: JsonMap) => (
                  <div key={entry.archive_key} className="truncate font-mono text-[10px] text-muted-foreground">
                    {entry.role_id} {entry.archive_key}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium">Daily Operating Loop</div>
                <Badge variant={summary.daily_operating_loop_ready ? "success" : "warning"}>
                  {summary.daily_operating_loop_ready ? "ready" : "check"}
                </Badge>
              </div>
              <div className="space-y-2">
                {dailyLoop.map((step: JsonMap) => (
                  <div key={step.step} className="rounded border border-primary/20 bg-background/25 p-2">
                    <div className="text-xs font-medium">{String(step.step || "").replace(/_/g, " ")}</div>
                    <div className="mt-1 text-[11px] text-muted-foreground">{step.action}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-primary/30 bg-primary/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-primary">Whole Organism Access</div>
                <Badge variant="outline">{(accessPolicy.universal_surfaces || []).length || 0} surfaces</Badge>
              </div>
              <div className="text-[11px] text-muted-foreground">{accessPolicy.purpose || "Waiting for access policy."}</div>
              <div className="mt-2 flex flex-wrap gap-1">
                {(accessPolicy.universal_surfaces || []).slice(0, 8).map((surface: string) => (
                  <Badge key={surface} variant="outline" className="text-[10px]">
                    {surface}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-success/30 bg-success/10 p-3">
              <div className="mb-2 text-sm font-medium text-success">Authority Boundaries</div>
              <div className="space-y-2">
                {boundaries.map((boundary: JsonMap) => (
                  <div key={boundary.id} className="rounded border border-success/20 bg-background/25 p-2">
                    <div className="text-xs font-medium">{boundary.title}</div>
                    <div className="mt-1 text-[11px] text-muted-foreground">{boundary.rule}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium">Capability Coverage</div>
                <Badge variant="outline">{coverage.length} sources</Badge>
              </div>
              <div className="space-y-2">
                {coverage.slice(0, 8).map((item: JsonMap) => (
                  <div key={item.id} className="flex items-center justify-between gap-2 rounded border border-border/30 bg-background/25 px-2 py-1.5">
                    <span className="truncate text-xs">{item.title}</span>
                    <Badge variant={item.covered ? "success" : "warning"}>{item.mapped_role_count || 0}</Badge>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-warning/30 bg-warning/10 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-warning">Work Orders</div>
                <Badge variant={workOrders.length ? "warning" : "success"}>{workOrders.length}</Badge>
              </div>
              <div className="space-y-2">
                {topWorkOrders.map((order: JsonMap) => (
                  <div key={order.id} className="rounded border border-warning/20 bg-background/25 p-2">
                    <div className="text-xs font-medium">{order.title}</div>
                    <div className="mt-1 text-[11px] text-muted-foreground">{order.exact_aureon_prompt}</div>
                  </div>
                ))}
                {!topWorkOrders.length ? <div className="text-xs text-muted-foreground">Every role has a mapped surface.</div> : null}
              </div>
            </div>

            <div className="rounded-md border border-border/40 bg-muted/10 p-3">
              <div className="mb-2 text-sm font-medium">Handoff Map</div>
              <div className="grid gap-1">
                {handoffMap.slice(0, 8).map((handoff: JsonMap, index: number) => (
                  <div key={`${handoff.from}-${handoff.to}-${index}`} className="truncate font-mono text-[11px] text-muted-foreground">
                    {handoff.from} {"->"} {handoff.to}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Stat({ icon: Icon, label, value }: { icon: any; label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-border/40 bg-muted/10 p-3">
      <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}
