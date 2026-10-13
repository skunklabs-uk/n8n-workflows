"""Behavioral seam: Inspection observations -> captured Slack, official n8n only.

Run: python3 -m unittest discover -s tests -p test_seo_daily.py -v
No live Google/Slack requests; each test owns an ephemeral native SQLite volume.

Native CLI limitation: Execute.init() does not initialize the Data Table module.
Sources (n8n@2.42.3): packages/cli/src/commands/execute.ts,
packages/cli/src/modules/data-table/data-table.module.ts in https://github.com/n8n-io/n8n.
The fixture is imported/published only in its disposable database before n8n start;
each observation uses docker exec node fetch over the container loopback webhook.
"""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid

IMAGE = "docker.n8n.io/n8nio/n8n:2.42.3@sha256:240eaa2a3d491adac5817aa4c3f1c521bb18ec79f6e448517158d5220ee0f37b"
WORKFLOW = Path(__file__).resolve().parents[1] / "workflows/baialupo-seo-daily.json"
URL = "https://www.baialupo.com/aviosuperficie"


class DailyInspectionTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="n8n-seo-daily-")
        self.volume = "n8n-seo-daily-" + uuid.uuid4().hex
        self.container = self.volume
        self.started = False
        subprocess.run(["docker", "volume", "create", self.volume], check=True, capture_output=True)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(subprocess.run, ["docker", "volume", "rm", self.volume],
                        check=True, capture_output=True)

    def docker_args(self):
        return ["docker", "run", "--pull=never", "--network", "none", "--user", "root",
                "-v", self.volume + ":/home/node/.n8n",
                "-v", self.directory.name + ":/fixtures",
                "-e", "N8N_USER_FOLDER=/home/node",
                "-e", "N8N_DIAGNOSTICS_ENABLED=false", "-e", "N8N_VERSION_NOTIFICATIONS_ENABLED=false",
                "-e", "N8N_ENCRYPTION_KEY=daily-local-fixture-only"]

    def command(self, args):
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
        if result.returncode:
            logs = subprocess.run(["docker", "logs", self.container], capture_output=True, text=True)
            self.fail("Native n8n command failed:\n" + result.stdout + result.stderr + logs.stdout + logs.stderr)
        return result.stdout

    def start_fixture(self):
        workflow = json.loads(WORKFLOW.read_text())
        workflow = copy.deepcopy(workflow)
        for item in workflow["nodes"]:
            if item["name"] == "Daily schedule":
                item.update(type="n8n-nodes-base.webhook", typeVersion=2,
                            webhookId="daily-fixture",
                            parameters={"httpMethod": "POST", "path": "daily-fixture",
                                        "responseMode": "lastNode", "responseData": "allEntries", "options": {}})
            elif item["name"] == "Observation date":
                for assignment in item["parameters"]["assignments"]["assignments"]:
                    if assignment["name"] == "observationDay":
                        assignment["value"] = "={{ $('Daily schedule').first().json.body.day }}"
            elif item["name"] == "Inspect priority URLs":
                # Only Google/time/trigger/Slack boundaries change. No application JS is extracted.
                fixture = ("const url = $json.url || " + json.dumps(URL) + "; "
                           "const result = url === " + json.dumps(URL)
                           + " ? $('Daily schedule').first().json.body.result"
                           + " : {inspectionResult:{indexStatusResult:{verdict:'PASS',coverageState:'Submitted and indexed',"
                           "indexingState:'INDEXING_ALLOWED',robotsTxtState:'ALLOWED',pageFetchState:'SUCCESSFUL',googleCanonical:url}}}; "
                           "return {json: result};")
                item.update(type="n8n-nodes-base.code", typeVersion=2,
                            parameters={"mode": "runOnceForEachItem", "jsCode": fixture})
                item.pop("credentials", None)
            elif item["name"] == "Notify homelab-alerts":
                text = item["parameters"]["text"]
                item.update(type="n8n-nodes-base.set", typeVersion=3.4,
                            parameters={"assignments": {"assignments": [
                                {"id": "text", "name": "capturedSlackText", "type": "string", "value": text}]},
                                "options": {}})
                item.pop("credentials", None)
        Path(self.directory.name, "workflow.json").write_text(json.dumps(workflow))
        self.command(self.docker_args() + ["--rm", IMAGE, "import:workflow", "--input=/fixtures/workflow.json"])
        # execute CLI does not initModules() in 2.42.3; Data Table requires the real server.
        # Publish only this disposable external-boundary fixture, never the repository workflow.
        self.command(self.docker_args() + ["--rm", IMAGE, "publish:workflow", "--id=" + workflow["id"]])
        self.addCleanup(subprocess.run, ["docker", "rm", "--force", self.container],
                        check=False, capture_output=True)
        self.command(self.docker_args() + ["--detach", "--name", self.container, IMAGE, "start"])
        ready = ("for(let i=0;i<120;i++){"
                 "try {const r=await fetch('http://127.0.0.1:5678/healthz/readiness');if(r.ok)process.exit(0);}catch{}"
                 "await new Promise(r=>setTimeout(r,500));}process.exit(1);")
        self.command(["docker", "exec", self.container, "node", "--input-type=module", "-e", ready])
        self.started = True

    def observe(self, day, result):
        if not self.started:
            self.start_fixture()
        request = json.dumps({"day": day, "result": result})
        script = ("const r=await fetch('http://127.0.0.1:5678/webhook/daily-fixture',"
                  "{method:'POST',headers:{'Content-Type':'application/json'},body:process.argv[1]});"
                  "const text=await r.text();if(!r.ok){console.error(text);process.exit(1);}console.log(text);")
        raw = self.command(["docker", "exec", self.container, "node", "--input-type=module", "-e", script, request])
        outputs = json.loads(raw) if raw.strip() else []
        if not isinstance(outputs, list):
            self.fail("Unexpected native webhook response: " + raw)
        # Only the replaced Slack transport can produce this field.
        return [item["capturedSlackText"] for item in outputs if "capturedSlackText" in item]

    def test_indexed_baseline_requires_two_daily_negatives_and_alerts_once(self):
        indexed = {"inspectionResult": {"indexStatusResult": {
            "verdict": "PASS", "coverageState": "Submitted and indexed",
            "indexingState": "INDEXING_ALLOWED", "robotsTxtState": "ALLOWED",
            "pageFetchState": "SUCCESSFUL", "googleCanonical": URL}}}
        negative = {"inspectionResult": {"indexStatusResult": {
            "verdict": "FAIL", "coverageState": "Excluded by noindex tag",
            "indexingState": "BLOCKED_BY_META_TAG", "robotsTxtState": "ALLOWED",
            "pageFetchState": "SUCCESSFUL", "googleCanonical": URL}}}
        self.assertEqual(self.observe("2026-10-10", indexed), [])
        self.assertEqual(self.observe("2026-10-11", negative), [])
        self.assertEqual(self.observe("2026-10-11", negative), [])
        alerts = self.observe("2026-10-12", negative)
        self.assertEqual(len(alerts), 1)
        self.assertIn(URL, alerts[0])
        self.assertIn("BLOCKED_BY_META_TAG", alerts[0])
        self.assertEqual(self.observe("2026-10-12", negative), [])
        self.assertEqual(self.observe("2026-10-13", negative), [])

    def test_unexpected_google_canonical_is_confirmed_even_when_verdict_passes(self):
        indexed = {"inspectionResult": {"indexStatusResult": {
            "verdict": "PASS", "coverageState": "Submitted and indexed",
            "indexingState": "INDEXING_ALLOWED", "robotsTxtState": "ALLOWED",
            "pageFetchState": "SUCCESSFUL", "googleCanonical": URL}}}
        canonical = "https://www.baialupo.com/posts"
        unexpected = copy.deepcopy(indexed)
        unexpected["inspectionResult"]["indexStatusResult"]["googleCanonical"] = canonical
        self.assertEqual(self.observe("2026-10-10", indexed), [])
        self.assertEqual(self.observe("2026-10-11", unexpected), [])
        alerts = self.observe("2026-10-12", unexpected)
        self.assertEqual(len(alerts), 1)
        self.assertIn(URL, alerts[0])
        self.assertIn("canonical", alerts[0].lower())
        self.assertIn(canonical, alerts[0])
        self.assertEqual(self.observe("2026-10-13", unexpected), [])

    def test_errors_and_missing_inspection_break_confirmation_without_mutating_baseline(self):
        indexed = {"inspectionResult": {"indexStatusResult": {
            "verdict": "PASS", "coverageState": "Submitted and indexed",
            "indexingState": "INDEXING_ALLOWED", "robotsTxtState": "ALLOWED",
            "pageFetchState": "SUCCESSFUL", "googleCanonical": URL}}}
        negative = {"inspectionResult": {"indexStatusResult": {
            "verdict": "FAIL", "coverageState": "Excluded by noindex tag",
            "indexingState": "BLOCKED_BY_META_TAG", "robotsTxtState": "ALLOWED",
            "pageFetchState": "SUCCESSFUL"}}}
        self.assertEqual(self.observe("2026-10-01", indexed), [])
        self.assertEqual(self.observe("2026-10-02", negative), [])
        self.assertEqual(self.observe("2026-10-03", {"error": {
            "code": 403, "status": "PERMISSION_DENIED", "message": "Insufficient property permissions"}}), [])
        self.assertEqual(self.observe("2026-10-04", {"error": {
            "code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Inspection quota exhausted"}}), [])
        self.assertEqual(self.observe("2026-10-05", {
            "inspectionResult": {"indexStatusResult": {"verdict": "PASS"}}}), [])
        self.assertEqual(self.observe("2026-10-06", negative), [])
        alerts = self.observe("2026-10-07", negative)
        self.assertEqual(len(alerts), 1)
        self.assertIn("Baseline indicizzata: 2026-10-01", alerts[0])
        self.assertIn("2026-10-06 / 2026-10-07", alerts[0])

    def test_pending_is_not_deindexing_but_lost_index_after_baseline_and_recovery_is(self):
        pending = {"inspectionResult": {"indexStatusResult": {
            "verdict": "NEUTRAL", "coverageState": "Discovered - currently not indexed",
            "indexingState": "INDEXING_STATE_UNSPECIFIED",
            "robotsTxtState": "ROBOTS_TXT_STATE_UNSPECIFIED",
            "pageFetchState": "PAGE_FETCH_STATE_UNSPECIFIED"}}}
        indexed = {"inspectionResult": {"indexStatusResult": {
            "verdict": "PASS", "coverageState": "Submitted and indexed",
            "indexingState": "INDEXING_ALLOWED", "robotsTxtState": "ALLOWED",
            "pageFetchState": "SUCCESSFUL", "googleCanonical": URL}}}
        lost = {"inspectionResult": {"indexStatusResult": {
            "verdict": "NEUTRAL", "coverageState": "Crawled - currently not indexed",
            "indexingState": "INDEXING_ALLOWED", "robotsTxtState": "ALLOWED",
            "pageFetchState": "SUCCESSFUL"}}}
        self.assertEqual(self.observe("2026-10-01", pending), [])
        self.assertEqual(self.observe("2026-10-02", pending), [])
        self.assertEqual(self.observe("2026-10-03", pending), [])
        self.assertEqual(self.observe("2026-10-04", indexed), [])
        self.assertEqual(self.observe("2026-10-05", lost), [])
        alerts = self.observe("2026-10-06", lost)
        self.assertEqual(len(alerts), 1)
        self.assertIn("Crawled - currently not indexed", alerts[0])
        self.assertIn("Baseline indicizzata: 2026-10-04", alerts[0])
        self.assertEqual(self.observe("2026-10-07", indexed), [])
        self.assertEqual(self.observe("2026-10-08", lost), [])
        alerts = self.observe("2026-10-09", lost)
        self.assertEqual(len(alerts), 1)
        self.assertIn("Baseline indicizzata: 2026-10-07", alerts[0])


if __name__ == "__main__":
    unittest.main()
