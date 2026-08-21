(() => {
  "use strict";

  const architectureEvidenceUrl = "../data/operator-evidence.json?v=aureon-v45-20260820";
  const status = document.querySelector("[data-live-status]");
  const detail = document.querySelector("[data-live-detail]");
  const fields = new Map(
    Array.from(document.querySelectorAll("[data-live-field]")).map((element) => [element.dataset.liveField, element])
  );

  function writeField(name, value) {
    const element = fields.get(name);
    if (element) element.textContent = value;
  }

  function setState(state, headline, supportingText) {
    document.body.dataset.liveState = state;
    if (status) status.textContent = headline;
    if (detail) detail.textContent = supportingText;
  }

  const architectureEvidence = document.querySelector("[data-architecture-evidence]");
  const architectureEvidenceStatus = document.querySelector("[data-architecture-evidence-status]");
  const architectureEvidenceDetail = document.querySelector("[data-architecture-evidence-detail]");
  const architectureEvidenceNote = document.querySelector("[data-architecture-evidence-note]");
  const architectureEvidenceFields = new Map(
    Array.from(document.querySelectorAll("[data-architecture-evidence-field]")).map((element) => [element.dataset.architectureEvidenceField, element])
  );

  function writeArchitectureField(name, value) {
    const element = architectureEvidenceFields.get(name);
    if (element) element.textContent = value;
  }

  function setArchitectureState(state, headline, supportingText) {
    if (architectureEvidence) architectureEvidence.dataset.operatorEvidenceState = state;
    if (architectureEvidenceStatus) architectureEvidenceStatus.textContent = headline;
    if (architectureEvidenceDetail) architectureEvidenceDetail.textContent = supportingText;
  }

  async function refreshArchitectureRecord() {
    if (!architectureEvidence) return;
    try {
      const response = await fetch(architectureEvidenceUrl, { cache: "no-store" });
      if (!response.ok) throw new Error("ARCHITECTURE_RECORD_UNAVAILABLE");

      const evidence = await response.json();
      if (!evidence || evidence.evidence_type !== "public_architecture_record") {
        throw new Error("ARCHITECTURE_RECORD_INVALID");
      }

      const layers = Array.isArray(evidence.architecture && evidence.architecture.layers)
        ? evidence.architecture.layers
        : [];
      const layerById = new Map(layers.map((layer) => [layer.id, layer]));
      const sourceRoutes = Array.isArray(evidence.source_routes) ? evidence.source_routes : [];
      const sourceRouteIds = new Set(sourceRoutes.map((route) => route.id));
      const requiredLayers = ["source", "provenance", "authority", "output"];
      const complete = requiredLayers.every((id) => layerById.has(id))
        && sourceRouteIds.has("repository")
        && sourceRouteIds.has("orcid")
        && sourceRouteIds.has("zenodo");

      writeArchitectureField("source", layerById.get("source")?.label || "Attributable sources");
      writeArchitectureField("provenance", layerById.get("provenance")?.label || "Provenance and claim state");
      writeArchitectureField("authority", layerById.get("authority")?.label || "Accountable human authority");
      writeArchitectureField("output", layerById.get("output")?.label || "Bounded outputs");
      writeArchitectureField("repository", sourceRouteIds.has("repository") ? "Public GitHub source" : "Open source route");
      writeArchitectureField("research", sourceRouteIds.has("orcid") && sourceRouteIds.has("zenodo") ? "ORCID + Zenodo" : "Open research routes");
      writeArchitectureField("diligence", evidence.disclosure_boundary ? "Qualified, scoped review" : "Public boundary");
      writeArchitectureField("reviewed", "Public orientation");

      setArchitectureState(
        complete ? "verified" : "attention",
        evidence.status || "Published architecture record",
        evidence.summary || "Public architecture and disclosure boundaries are available for review."
      );
      if (architectureEvidenceNote) {
        architectureEvidenceNote.textContent = evidence.disclosure_boundary
          || "Public architecture supports inspection; supporting diligence requires a qualified, scoped review.";
      }
    } catch (_error) {
      writeArchitectureField("source", "Open public source");
      writeArchitectureField("provenance", "See platform overview");
      writeArchitectureField("authority", "Human decision gate");
      writeArchitectureField("output", "Bounded records");
      writeArchitectureField("repository", "Open GitHub");
      writeArchitectureField("research", "Open research");
      writeArchitectureField("diligence", "Qualified access");
      writeArchitectureField("reviewed", "See source");
      setArchitectureState(
        "unavailable",
        "Public architecture record unavailable",
        "The primary repository, research portfolio and platform overview remain available from their direct public links."
      );
      if (architectureEvidenceNote) {
        architectureEvidenceNote.textContent = "Supporting diligence is shared only in a qualified, scoped review.";
      }
    }
  }

  function hydratePublicRepositorySignal() {
    writeField("visibility", "Public source");
    writeField("branch", "Inspect source");
    writeField("pushed", "See repository");
    writeField("updated", "See repository");
    setState(
      "source-linked",
      "Public source available",
      "Open the primary repository for its current branch and history. This page does not imply release, customer use or independent assurance from repository metadata."
    );
  }

  hydratePublicRepositorySignal();
  refreshArchitectureRecord();
})();
