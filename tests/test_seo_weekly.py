"""Search Analytics fixtures -> prepared Slack report, through official n8n.

Only Schedule, Google, Slack and time are replaced in a temporary full workflow.
No live credentials, network, application-JS extraction or simulated engine.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflows" / "baialupo-seo-weekly.json"
IMAGE = "docker.n8n.io/n8nio/n8n:2.42.3@sha256:240eaa2a3d491adac5817aa4c3f1c521bb18ec79f6e448517158d5220ee0f37b"


class WeeklyReportTest(unittest.TestCase):
    def run_report(self, responses, now="2026-10-13T01:00:00Z"):
        workflow = json.loads(WORKFLOW.read_text())
        workflow = copy.deepcopy(workflow)
        # Freeze the time boundary, not the interval calculation.
        workflow = json.loads(json.dumps(workflow).replace("$now", f"DateTime.fromISO('{now}')"))
        for node in workflow["nodes"]:
            kind = node["type"]
            if kind == "n8n-nodes-base.scheduleTrigger":
                node.update(type="n8n-nodes-base.manualTrigger", typeVersion=1, parameters={})
            elif kind == "n8n-nodes-base.httpRequest":
                response = responses[node["name"]]
                request = node["parameters"]["jsonBody"].removeprefix("=")
                if request.startswith("{{") and request.endswith("}}"):
                    request = request[2:-2].strip()
                node.update(type="n8n-nodes-base.code", typeVersion=2, parameters={
                    "jsCode": "return [{json: Object.assign(" + json.dumps(response) + ", {fixtureRequest: (" + request + ")})}];",
                })
                node.pop("credentials", None)
            elif kind == "n8n-nodes-base.slack":
                text = node["parameters"]["text"]
                channel = node["parameters"]["channelId"]["value"]
                node.update(type="n8n-nodes-base.set", typeVersion=3.4, parameters={
                    "assignments": {"assignments": [
                        {"id": "text", "name": "text", "type": "string", "value": text},
                        {"id": "channel", "name": "channel", "type": "string", "value": channel},
                    ]}, "options": {},
                })
                node.pop("credentials", None)
        with tempfile.TemporaryDirectory(prefix="n8n-weekly-") as directory:
            os.chmod(directory, 0o777)
            Path(directory, "workflow.json").write_text(json.dumps(workflow))
            result = subprocess.run([
                "docker", "run", "--rm", "--pull=never", "--network", "none",
                "--mount", f"type=bind,src={directory},dst=/fixtures",
                "-e", "N8N_DIAGNOSTICS_ENABLED=false", "-e", "N8N_VERSION_NOTIFICATIONS_ENABLED=false",
                "-e", "N8N_TEMPLATES_ENABLED=false",
                "--entrypoint", "/bin/sh", IMAGE, "-c",
                "n8n import:workflow --input=/fixtures/workflow.json && n8n execute --id=" + workflow["id"] + " --rawOutput",
            ], text=True, capture_output=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            execution = None
            decoder = json.JSONDecoder()
            for index, character in enumerate(result.stdout):
                if character != "{":
                    continue
                try:
                    candidate, _ = decoder.raw_decode(result.stdout[index:])
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and "data" in candidate and "resultData" in candidate["data"]:
                    execution = candidate
                    break
            self.assertIsNotNone(execution, result.stdout + result.stderr)
            data = execution["data"]["resultData"]
            self.assertNotIn("error", data, data)
            outputs = data["runData"]["Notify homelab-alerts"]
            self.assertEqual(len(outputs), 1, "One bounded weekly notification")
            messages = outputs[0]["data"]["main"][0]
            self.assertEqual(len(messages), 1, "One bounded weekly notification")
            return messages[0]["json"], data["runData"]

    def test_final_date_rows_produce_weighted_report_with_missing_days(self):
        responses = {
            "Query Dates": {"statusCode": 200, "body": {"rows": [
                {"keys": ["2026-10-03"], "clicks": 10, "impressions": 100, "ctr": 0.1, "position": 2},
                {"keys": ["2026-10-09"], "clicks": 30, "impressions": 300, "ctr": 0.1, "position": 6},
            ]}},
            "Query Pages": {"statusCode": 200, "body": {"rows": [
                {"keys": ["https://baialupo.com/"], "clicks": 999, "impressions": 9999, "position": 1},
            ]}},
            "Query Queries": {"statusCode": 200, "body": {"rows": [
                {"keys": ["baialupo"], "clicks": 888, "impressions": 8888, "position": 1},
            ]}},
        }
        message, runs = self.run_report(responses)
        self.assertEqual(message["channel"], "C0BNWAM4R8D")
        text = message["text"]
        for expected in ["2026-10-03", "2026-10-09", "America/Los_Angeles", "final", "Clic: 40", "Impressioni: 400", "CTR: 10.00%", "Posizione: 5.00", "2/7", "2026-10-04", "2026-10-08", "https://baialupo.com/", "baialupo", "campione"]:
            self.assertIn(expected, text)
        for name, dimension in [("Query Dates", "date"), ("Query Pages", "page"), ("Query Queries", "query")]:
            request = runs[name][0]["data"]["main"][0][0]["json"]["fixtureRequest"]
            self.assertEqual(request["startDate"], "2026-10-03")
            self.assertEqual(request["endDate"], "2026-10-09")
            self.assertEqual(request["dataState"], "final")
            self.assertEqual(request["dimensions"], [dimension])

    def test_missing_dates_and_query_error_preserve_available_page_sample(self):
        message, _ = self.run_report({
            "Query Dates": {"statusCode": 200, "body": {"rows": []}},
            "Query Pages": {"statusCode": 200, "body": {"rows": [
                {"keys": ["https://baialupo.com/pagina"], "clicks": 7, "impressions": 70, "position": 3},
            ]}},
            "Query Queries": {"statusCode": 403, "body": {"error": {"code": 403, "message": "permission denied"}}},
        })
        text = message["text"]
        for expected in ["nessun dato utile", "0/7", "2026-10-03", "2026-10-09", "https://baialupo.com/pagina", "clic 7", "403", "Query", "nessun retry"]:
            self.assertIn(expected, text)
        for misleading in ["Clic: 0", "Impressioni: 0", "CTR: 0", "NaN"]:
            self.assertNotIn(misleading, text)

    def test_oauth_and_rate_limit_failures_do_not_hide_useful_queries(self):
        message, _ = self.run_report({
            "Query Dates": {"error": {"message": "OAuth credential unavailable"}},
            "Query Pages": {"statusCode": 429, "body": {"error": {"code": 429, "message": "rate limit"}}},
            "Query Queries": {"statusCode": 200, "body": {"rows": [
                {"keys": ["ricetta baialupo"], "clicks": 9, "impressions": 90, "position": 4},
            ]}},
        })
        text = message["text"]
        for expected in ["nessun dato utile", "OAuth", "429", "ricetta baialupo", "clic 9", "nessun retry"]:
            self.assertIn(expected, text)
        for misleading in ["Clic: 0", "Impressioni: 0", "NaN"]:
            self.assertNotIn(misleading, text)

    def test_zero_impression_rows_do_not_certify_zero_traffic(self):
        message, _ = self.run_report({
            "Query Dates": {"statusCode": 200, "body": {"rows": [
                {"keys": ["2026-10-03"], "clicks": 0, "impressions": 0, "position": 0},
            ]}},
            "Query Pages": {"statusCode": 200, "body": {}},
            "Query Queries": {"statusCode": 200, "body": {}},
        })
        text = message["text"]
        self.assertIn("1/7", text)
        self.assertIn("Totali: nessun dato utile", text)
        self.assertIn("non equivale a zero traffico accertato", text)
        for misleading in ["Clic: 0", "Impressioni: 0", "CTR: 0", "Posizione: 0", "NaN"]:
            self.assertNotIn(misleading, text)


if __name__ == "__main__":
    unittest.main()
