import importlib.util
import io
import json
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path, PureWindowsPath
import sys

import pytest

DIRECTORY = Path(__file__).parents[1] / "deployment/google-cloud"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("build_release_bundle", DIRECTORY / "build_release_bundle.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)
operator_closure = sys.modules["operator_runtime_closure"]
FRONTEND_ENV = {
    "VITE_REQUIRE_AUTH": "1",
    "VITE_SUPABASE_URL": "https://fixture.supabase.co",
    "VITE_SUPABASE_PUBLISHABLE_KEY": "fixture-public-key-value",
}


def bridge_certificate_receipt(tmp_path, revision="a" * 40):
    path = tmp_path / "bridge-certificate-receipt.json"
    now = datetime.now(UTC)
    path.write_text(
        json.dumps(
            {
                "schema": bundle.BRIDGE_CERTIFICATE_RECEIPT_SCHEMA,
                "status": "passed",
                "project": "aureon-trading",
                "zone": "europe-west1-b",
                "instance": "aureon-sero-20260906",
                "source_revision": revision,
                "recorded_at": now.isoformat(),
                "certificate_path": "/etc/aureon-public/bridge-cert.pem",
                "algorithm": "x509-der-sha256",
                "certificate_sha256": "c" * 64,
                "required_ip_sans": ["10.40.0.2"],
                "not_before": (now - timedelta(days=1)).isoformat(),
                "not_after": (now + timedelta(days=30)).isoformat(),
                "minimum_remaining_validity_seconds": 86_400,
                "private_key_included": False,
                "secret_values_recorded": False,
            }
        ),
        encoding="utf-8",
    )
    return path, bundle.digest(path.read_bytes())


def bind_git(monkeypatch, path: Path, *, revision="a" * 40, tracked=(), dirty=False):
    tracked = set(tracked)

    def fake_git(_source, *args):
        if args == ("rev-parse", "--show-toplevel"):
            return str(path.resolve())
        if args == ("rev-parse", "--verify", "HEAD"):
            return revision
        if args == ("rev-parse", "--verify", "HEAD^{tree}"):
            return "b" * 40
        if args == ("status", "--porcelain=v1", "--untracked-files=no"):
            return " M tracked.py" if dirty else ""
        if args[:3] == ("ls-files", "--error-unmatch", "--") and args[3] in tracked:
            return args[3]
        if args == (
            "ls-tree",
            "-r",
            "--name-only",
            revision,
            "--",
            bundle.OPERATOR_PACKAGE_PREFIX.rstrip("/"),
        ):
            return "\n".join(
                sorted(
                    path
                    for path in tracked
                    if path.startswith(bundle.OPERATOR_PACKAGE_PREFIX)
                )
            )
        raise bundle.ReleaseError("source_git_identity_unavailable")

    monkeypatch.setattr(bundle, "_git", fake_git)
    monkeypatch.setattr(
        bundle,
        "_git_blob",
        lambda checkout, _revision, relative: (checkout / relative).read_bytes(),
    )
    return revision


def test_explicit_bundle_keeps_private_files_out_and_binds_reviewed_hash(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "aureon_fusion/state").mkdir(parents=True)
    code = source / "aureon_fusion/reader.py"
    code.write_bytes(b"VALUE = 1\n")
    private = source / "aureon_fusion/state/approval.json"
    private.write_text('{"private fixture":"must not travel"}')
    revision = bind_git(monkeypatch, source, tracked={"aureon_fusion/reader.py"})
    selected = [{"path": "aureon_fusion/reader.py", "sha256": bundle.digest(code.read_bytes())}]
    out = tmp_path / "bundle"
    manifest = bundle.build(source, selected, out, revision, "20260911T230000Z-aaaaaaaa")
    assert len(manifest["files"]) == 1
    assert (out / "files/aureon_fusion/reader.py").read_bytes() == code.read_bytes()
    assert not (out / "files/aureon_fusion/state").exists()
    assert json.loads((out / "manifest.json").read_text())["contains_runtime_state"] is False
    code.write_bytes(b"VALUE = 2\n")
    with pytest.raises(bundle.ReleaseError, match="reviewed_source_hash_changed|tracked_source_checkout_must_be_clean"):
        bundle.build(source, selected, tmp_path / "second", revision, "20260911T230001Z-aaaaaaaa")
    assert not (tmp_path / "second").exists()


def test_no_bundle_overwrite_or_runtime_selection(tmp_path):
    source = tmp_path / "source"
    (source / "aureon_fusion").mkdir(parents=True)
    with pytest.raises(bundle.ReleaseError, match="runtime_or_private"):
        bundle.build(source, ["aureon_fusion/state/approval.json"], tmp_path / "out", "a" * 40, "20260911T230000Z-aaaaaaaa")
    assert not (tmp_path / "out").exists()
    with pytest.raises(bundle.ReleaseError, match="destination_must_be_new"):
        bundle.build(source, ["aureon_fusion/reader.py"], source, "a" * 40, "20260911T230000Z-aaaaaaaa")


def test_revision_must_be_current_clean_git_head(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "aureon_fusion").mkdir(parents=True)
    code = source / "aureon_fusion/reader.py"
    code.write_text("VALUE = 1\n")
    revision = bind_git(monkeypatch, source, tracked={"aureon_fusion/reader.py"})
    selected = [{"path": "aureon_fusion/reader.py", "sha256": bundle.digest(code.read_bytes())}]
    with pytest.raises(bundle.ReleaseError, match="revision_does_not_match_git_head"):
        bundle.build(source, selected, tmp_path / "wrong", "b" * 40, "20260911T230002Z-aaaaaaaa")
    code.write_text("VALUE = 2\n")
    selected[0]["sha256"] = bundle.digest(code.read_bytes())
    bind_git(monkeypatch, source, revision=revision, tracked={"aureon_fusion/reader.py"}, dirty=True)
    with pytest.raises(bundle.ReleaseError, match="tracked_source_checkout_must_be_clean"):
        bundle.build(source, selected, tmp_path / "dirty", revision, "20260911T230003Z-aaaaaaaa")


def test_frontend_dist_selection_must_be_complete(tmp_path, monkeypatch):
    source = tmp_path / "source"
    src = source / "aureon-os-upstream/frontend/src"
    dist = source / "aureon-os-upstream/frontend/dist/assets"
    src.mkdir(parents=True)
    dist.mkdir(parents=True)
    (src / "main.ts").write_text("export {};\n")
    index = dist.parent / "index.html"
    asset = dist / "app.js"
    index.write_text('<script src="/assets/app.js"></script>')
    asset.write_text("console.log('ok')")
    revision = bind_git(
        monkeypatch, source, tracked={
            "aureon-os-upstream/frontend/src/main.ts",
            "aureon-os-upstream/frontend/dist/index.html",
        }
    )
    selected = [
        {"path": "aureon-os-upstream/frontend/src/main.ts", "sha256": bundle.digest((src / "main.ts").read_bytes())},
        {"path": "aureon-os-upstream/frontend/dist/index.html", "sha256": bundle.digest(index.read_bytes())},
    ]
    with pytest.raises(bundle.ReleaseError, match="complete_frontend_dist_inventory_required"):
        bundle.build(source, selected, tmp_path / "partial", revision, "20260911T230004Z-aaaaaaaa")
    selected.append({"path": "aureon-os-upstream/frontend/dist/assets/app.js", "sha256": bundle.digest(asset.read_bytes())})
    rebuilt = {
        "aureon-os-upstream/frontend/dist/index.html": index.read_bytes(),
        "aureon-os-upstream/frontend/dist/assets/app.js": asset.read_bytes(),
    }
    manifest = bundle.build(
        source,
        selected,
        tmp_path / "complete",
        revision,
        "20260911T230006Z-aaaaaaaa",
        frontend_build_environment=FRONTEND_ENV,
        frontend_builder=lambda *_: (rebuilt, {"node": "v22.0.0", "npm": "10.0.0"}),
    )
    assert manifest["source_git_revision"] == revision
    assert manifest["frontend_dist"]["files"] == 2
    assert manifest["frontend_dist"]["schema"] == bundle.FRONTEND_BUILD_SCHEMA
    assert manifest["frontend_dist"]["source_git_tree"] == "b" * 40
    assert "fixture-public-key-value" not in json.dumps(manifest)

    changed = dict(rebuilt)
    changed["aureon-os-upstream/frontend/dist/assets/app.js"] = b"different"
    with pytest.raises(bundle.ReleaseError, match="not_reproducible_from_commit"):
        bundle.build(
            source,
            selected,
            tmp_path / "mismatch",
            revision,
            "20260911T230007Z-aaaaaaaa",
            frontend_build_environment=FRONTEND_ENV,
            frontend_builder=lambda *_: (
                changed,
                {"node": "v22.0.0", "npm": "10.0.0"},
            ),
        )


def test_frontend_dist_inventory_sorts_normalized_paths_not_windows_paths():
    class VirtualWindowsPath(PureWindowsPath):
        def is_symlink(self):
            return False

        def is_dir(self):
            return self.name == "dist"

        def is_file(self):
            return self.name != "dist"

        def rglob(self, pattern):
            assert pattern == "*"
            return iter(
                (
                    self / "assets/Zed.js",
                    self / "assets/alpha.js",
                    self / "index.html",
                )
            )

    source = VirtualWindowsPath("C:/source")
    windows_paths = list((source / "aureon-os-upstream/frontend/dist").rglob("*"))
    windows_order = [path.relative_to(source).as_posix() for path in sorted(windows_paths)]
    string_order = sorted(windows_order)
    assert windows_order != string_order

    assert bundle._frontend_dist_inventory(source) == string_order


def test_frontend_archive_accepts_directory_ancestors_and_exact_prefix(tmp_path):
    content = b'{"name":"frontend"}\n'
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name in (
            "aureon-os-upstream",
            bundle.FRONTEND_SOURCE_ROOT,
            f"{bundle.FRONTEND_SOURCE_ROOT}/src",
        ):
            member = tarfile.TarInfo(name)
            member.type = tarfile.DIRTYPE
            archive.addfile(member)
        member = tarfile.TarInfo(f"{bundle.FRONTEND_SOURCE_ROOT}/package.json")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))

    destination = tmp_path / "extracted"
    bundle._extract_regular_archive(
        stream.getvalue(), destination, bundle.FRONTEND_SOURCE_ROOT
    )

    assert (
        destination / bundle.FRONTEND_SOURCE_ROOT / "package.json"
    ).read_bytes() == content


@pytest.mark.parametrize(
    ("name", "member_type"),
    (
        ("aureon-os-upstream", tarfile.REGTYPE),
        (bundle.FRONTEND_SOURCE_ROOT, tarfile.REGTYPE),
        ("aureon-os-upstream/sibling", tarfile.DIRTYPE),
        (f"{bundle.FRONTEND_SOURCE_ROOT}/../escape", tarfile.REGTYPE),
        (f"{bundle.FRONTEND_SOURCE_ROOT}/link", tarfile.SYMTYPE),
        (f"{bundle.FRONTEND_SOURCE_ROOT}/device", tarfile.CHRTYPE),
    ),
)
def test_frontend_archive_rejects_unsafe_root_members(
    tmp_path, name, member_type
):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        member = tarfile.TarInfo(name)
        member.type = member_type
        if member_type == tarfile.REGTYPE:
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))
        else:
            archive.addfile(member)

    with pytest.raises(bundle.ReleaseError, match="frontend_commit_archive_invalid"):
        bundle._extract_regular_archive(
            stream.getvalue(), tmp_path / "rejected", bundle.FRONTEND_SOURCE_ROOT
        )


@pytest.mark.parametrize(
    ("platform", "npm_name"), (("nt", "npm.cmd"), ("posix", "npm"))
)
def test_frontend_toolchain_resolves_platform_npm_wrapper(platform, npm_name):
    calls = []

    def resolve(name):
        calls.append(name)
        return {npm_name: f"/tools/{npm_name}", "node": "/tools/node"}.get(name)

    assert bundle._frontend_toolchain_executables(
        platform=platform, resolver=resolve
    ) == (f"/tools/{npm_name}", "/tools/node")
    assert calls == [npm_name, "node"]


def test_frontend_toolchain_does_not_fallback_to_windows_npm_shell_script():
    calls = []

    def resolve(name):
        calls.append(name)
        return {"npm": "C:/Program Files/nodejs/npm", "node": "C:/node.exe"}.get(name)

    with pytest.raises(bundle.ReleaseError, match="frontend_pinned_builder_unavailable"):
        bundle._frontend_toolchain_executables(platform="nt", resolver=resolve)
    assert calls == ["npm.cmd", "node"]


def test_operator_bundle_binds_the_complete_commit_tree_runtime(
    tmp_path, monkeypatch
):
    source = tmp_path / "source"
    package_tree = [
        "aureon-os-upstream/aureon/__init__.py",
        "aureon-os-upstream/aureon/operator/__init__.py",
        "aureon-os-upstream/aureon/operator/operator_server.py",
        "aureon-os-upstream/aureon/operator/transitive_dependency.py",
    ]
    selected_paths = operator_closure.required_operator_runtime_sources(package_tree)
    selected = []
    for index, relative in enumerate(selected_paths):
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        data = f"VALUE = {index}\n".encode()
        target.write_bytes(data)
        selected.append({"path": relative, "sha256": bundle.digest(data)})
    revision = bind_git(monkeypatch, source, tracked=selected_paths)
    receipt, receipt_sha = bridge_certificate_receipt(tmp_path, revision)

    manifest = bundle.build(
        source,
        selected,
        tmp_path / "operator-bundle",
        revision,
        "20260913T120000Z-aaaaaaaa",
        bridge_certificate_receipt=receipt,
        bridge_certificate_receipt_sha256=receipt_sha,
    )

    operator = manifest["operator_runtime"]
    assert operator["source_git_tree"] == "b" * 40
    assert operator["sources"] == list(selected_paths)
    assert operator["files"] == len(selected_paths)
    assert manifest["public_bridge"]["certificate"]["receipt"]["sha256"] == receipt_sha
    assert manifest["public_bridge"]["certificate"]["sha256"] == "c" * 64
    assert manifest["public_bridge"]["certificate"]["receipt"][
        "required_ip_sans"
    ] == ["10.40.0.2"]
    assert manifest["public_bridge"]["certificate"]["receipt"][
        "minimum_remaining_validity_seconds"
    ] == 86_400
    assert "private_key" not in json.dumps(manifest)


def test_certificate_receipt_requires_current_bound_ip_certificate(tmp_path):
    revision = "a" * 40
    receipt, _receipt_sha = bridge_certificate_receipt(tmp_path, revision)
    value = json.loads(receipt.read_text(encoding="utf-8"))
    value["required_ip_sans"] = ["10.40.0.3"]
    receipt.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(
        bundle.ReleaseError,
        match="bridge_certificate_fingerprint_receipt_invalid",
    ):
        bundle._certificate_receipt(
            receipt,
            bundle.digest(receipt.read_bytes()),
            revision,
        )


def test_operator_bundle_rejects_a_partial_runtime(tmp_path, monkeypatch):
    source = tmp_path / "source"
    package_tree = [
        "aureon-os-upstream/aureon/__init__.py",
        "aureon-os-upstream/aureon/operator/__init__.py",
        "aureon-os-upstream/aureon/operator/operator_server.py",
    ]
    required = operator_closure.required_operator_runtime_sources(package_tree)
    selected_paths = required[:-1]
    selected = []
    for relative in selected_paths:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"VALUE = 1\n")
        selected.append(
            {"path": relative, "sha256": bundle.digest(target.read_bytes())}
        )
    revision = bind_git(monkeypatch, source, tracked=required)
    receipt, receipt_sha = bridge_certificate_receipt(tmp_path, revision)

    with pytest.raises(
        bundle.ReleaseError, match="complete_operator_runtime_sources_required"
    ):
        bundle.build(
            source,
            selected,
            tmp_path / "partial-operator",
            revision,
            "20260913T120001Z-aaaaaaaa",
            bridge_certificate_receipt=receipt,
            bridge_certificate_receipt_sha256=receipt_sha,
        )
