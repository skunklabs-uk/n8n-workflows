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
                "-e", "N8N_LOG_LEVEL=debug",
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
        # Observe the Slack boundary even when a later native node fails the execution.
        Path(self.directory.name, "slack-fixture.js").write_text(
            "const http=require('node:http');const messages=[];"
            "http.createServer(async(req,res)=>{"
            "if(req.method==='POST'){let body='';for await(const c of req)body+=c;"
            "messages.push(JSON.parse(body).text);}else if(req.method==='DELETE')messages.length=0;"
            "res.setHeader('Content-Type','application/json');"
            "res.end(JSON.stringify(req.method==='GET'?messages:{ok:true}));"
            "}).listen(5677,'127.0.0.1');")
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
                           "const request = $('Daily schedule').first().json.body; "
                           "const result = url === (request.targetUrl || " + json.dumps(URL) + ")"
                           + " ? request.result"
                           + " : {inspectionResult:{indexStatusResult:{verdict:'PASS',coverageState:'Submitted and indexed',"
                           "indexingState:'INDEXING_ALLOWED',robotsTxtState:'ALLOWED',pageFetchState:'SUCCESSFUL',googleCanonical:url}}}; "
                           "return {json: result};")
                item.update(type="n8n-nodes-base.code", typeVersion=2,
                            parameters={"mode": "runOnceForEachItem", "jsCode": fixture})
                item.pop("credentials", None)
            elif item["name"] == "Notify homelab-alerts":
                text = item["parameters"]["text"]
                item.update(type="n8n-nodes-base.httpRequest", typeVersion=4.4,
                            parameters={"method": "POST", "url": "http://127.0.0.1:5677/slack",
                                        "sendBody": True, "bodyParameters": {"parameters": [
                                            {"name": "text", "value": text}]},
                                        "options": {"timeout": 10000}})
                item.pop("credentials", None)
        Path(self.directory.name, "workflow.json").write_text(json.dumps(workflow))
        self.command(self.docker_args() + ["--rm", IMAGE, "import:workflow", "--input=/fixtures/workflow.json"])
        # execute CLI does not initModules() in 2.42.3; Data Table requires the real server.
        # Publish only this disposable external-boundary fixture, never the repository workflow.
        self.command(self.docker_args() + ["--rm", IMAGE, "publish:workflow", "--id=" + workflow["id"]])
        self.addCleanup(subprocess.run, ["docker", "rm", "--force", self.container],
                        check=False, capture_output=True)
        self.command(self.docker_args() + ["--detach", "--name", self.container,
                                         "--entrypoint", "/bin/sh", IMAGE, "-c",
                                         "node /fixtures/slack-fixture.js & exec n8n start"])
        ready = ("for(let i=0;i<120;i++){"
                 "try {const r=await fetch('http://127.0.0.1:5678/healthz/readiness');"
                 "const s=await fetch('http://127.0.0.1:5677/slack');if(r.ok&&s.ok)process.exit(0);}catch{}"
                 "await new Promise(r=>setTimeout(r,500));}process.exit(1);")
        self.command(["docker", "exec", self.container, "node", "--input-type=module", "-e", ready])
        self.started = True

    def post_observation(self, day, result, url=URL):
        if not self.started:
            self.start_fixture()
        request = json.dumps({"day": day, "result": result, "targetUrl": url})
        script = ("await fetch('http://127.0.0.1:5677/slack',{method:'DELETE'});"
                  "const r=await fetch('http://127.0.0.1:5678/webhook/daily-fixture',"
                  "{method:'POST',headers:{'Content-Type':'application/json'},body:process.argv[1]});"
                  "const body=await r.text();"
                  "const alerts=await(await fetch('http://127.0.0.1:5677/slack')).json();"
                  "console.log(JSON.stringify({status:r.status,body,alerts}));")
        raw = self.command(["docker", "exec", self.container, "node", "--input-type=module", "-e", script, request])
        return json.loads(raw)

    def observe(self, day, result, url=URL, expected_failure=False):
        response = self.post_observation(day, result, url)
        self.assertEqual(response["status"], 500 if expected_failure else 200, response["body"])
        return response["alerts"]

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
            "code": 403, "status": "PERMISSION_DENIED", "message": "Insufficient property permissions"}},
            expected_failure=True), [])
        self.assertEqual(self.observe("2026-10-04", {"error": {
            "code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Inspection quota exhausted"}},
            expected_failure=True), [])
        self.assertEqual(self.observe("2026-10-05", {
            "inspectionResult": {"indexStatusResult": {"verdict": "PASS"}}},
            expected_failure=True), [])
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

    def test_oauth_failure_is_operationally_explicit_without_losing_other_url_baselines(self):
        failure = self.post_observation("2026-10-01", {"error": {
            "code": 401, "status": "UNAUTHENTICATED", "message": "OAuth credential unavailable"}})
        self.assertEqual(failure["status"], 500, failure["body"])
        self.assertEqual(failure["alerts"], [])
        logs = subprocess.run(["docker", "logs", self.container], capture_output=True, text=True, check=True)
        diagnostics = logs.stdout + logs.stderr
        self.assertIn("401", diagnostics)
        self.assertIn("UNAUTHENTICATED", diagnostics)
        other_url = "https://www.baialupo.com/posts"
        negative = {"inspectionResult": {"indexStatusResult": {
            "verdict": "FAIL", "coverageState": "Excluded by noindex tag",
            "indexingState": "BLOCKED_BY_META_TAG", "robotsTxtState": "ALLOWED",
            "pageFetchState": "SUCCESSFUL"}}}
        self.assertEqual(self.observe("2026-10-02", negative, other_url), [])
        alerts = self.observe("2026-10-03", negative, other_url)
        self.assertEqual(len(alerts), 1)
        self.assertIn(other_url, alerts[0])
        self.assertIn("Baseline indicizzata: 2026-10-01", alerts[0])


if __name__ == "__main__":
    unittest.main()
