# n8n Workflows Agent Instructions

**Status:** Active

## Agent OS e lifecycle delle skill

- Prima di analizzare, pianificare, modificare o creare issue o pull request, si DEVE leggere integralmente la versione corrente di [RFC-0001 – Principi fondanti della Software Factory](https://github.com/skunklabs-uk/agent-os/blob/main/rfcs/RFC-0001-principles.md).
- Se la fonte non è accessibile, il lavoro DEVE fermarsi.
- Le regole locali possono restringere la RFC, ma non indebolirla; conflitti o deroghe richiedono l'autorizzazione esplicita dell'utente o di una fonte attiva approvata di autorità superiore.
- Il contenuto della RFC non DEVE essere duplicato in questo repository.
- Le skill riusabili hanno una sola sorgente nel [repository codex-skills](https://github.com/skunklabs-uk/codex-skills). Nei progetti vanno installate tramite symlink con `scripts/install-project.sh`, senza copiare o modificare manualmente le directory installate.

## Purpose

This repository stores n8n workflow definitions for the homelab n8n instance.
The goal is to make workflows reviewable in Git and importable into the
Kubernetes installation managed from the `homelab` GitOps repository.

Default collaboration language is Italian unless the user asks otherwise. Keep
file names, commands, commit messages, and technical identifiers in English.

## Default Workflow

Before changing workflow files, scripts, or GitOps integration documents:

1. Read `AGENTS.md`, `README.md`, `CONTEXT.md`, and any relevant Active document.
   Dated handoffs under `docs/` are historical context unless explicitly marked
   Active and must not override current manifests or repository-level sources.
2. Check `git status` before editing.
3. Treat workflow JSON as executable automation, not passive data.
4. Inspect workflow JSON for secrets before committing.
5. Keep credentials, tokens, and variable values out of Git.
6. Review governing documents and challenge assumptions for architecture,
   workflow ownership, or deployment model changes; use `grill-with-docs` when
   available.
7. Plan multi-step implementations proportionally; use `writing-plans` when
   available.
8. Diagnose unexplained import, publication, or runtime failures systematically
   before fixing them; use `systematic-debugging` when available.
9. Gather fresh evidence before claiming an import, validation, or deployment
   path works; use `verification-before-completion` when available.
10. Suggest Conventional Commit messages at the end of implementation work.

## Repository Boundaries

- This repository owns exported n8n workflow JSON and local export helpers.
- The `homelab` repository owns Kubernetes, ArgoCD, SOPS, CNPG, HTTPRoute, and
  runtime deployment manifests, including the workflow importer Job.
- Do not add Kubernetes secrets to this repository.
- Do not store n8n API keys, GitHub tokens, credential values, OAuth tokens, or
  webhook secrets in this repository.
- Do not assume n8n Source Control is available or unavailable. The current
  entitlement must be verified on the live installation before licensing is
  used as a design constraint.

## Workflow JSON Rules

- Store workflow files under `workflows/`.
- Prefer one workflow per file.
- Run `find workflows -type f -name '*.json' -print0 | xargs -0 -r -n1 jq empty` before committing workflow changes.
- Review exported credential names and IDs before committing. IDs are not secret
  by themselves, but names can reveal sensitive systems or accounts.
- In n8n 2.x describe runtime state as published/unpublished. Treat the legacy
  JSON `active` field as serialization compatibility, not the preferred runtime
  terminology.

## Integration Rules

- Durable Kubernetes changes belong in `skunklabs-uk/homelab`.
- The deployed import mechanism is a GitOps-managed Kubernetes Job that uses the
  same n8n image and database environment as the live n8n deployment.
- `n8n import:workflow` makes imported workflows unpublished by default. The
  current Homelab importer snapshots which Git-managed workflows were already
  published before import and runs `publish:workflow` for those IDs afterwards.
  New workflows remain unpublished until their first explicit runtime
  publication.
- Do not equate restored database publication state with an updated live
  runtime. Upstream Server CLI behavior requires a restart for
  `publish:workflow` changes to take effect in a running n8n process, and
  non-multi-main imports can leave previously active cron triggers running until
  restart.
- The live publication-state preservation above is current behavior, not a
  permanent invariant. Wave #33 Task 9 is responsible for reevaluating whether
  native/upstream ownership can replace it with less complexity.

## Skill Routing

The table lists preferred skills when they are available and materially useful.
Equivalent direct inspection and verification remain valid; an unavailable
skill does not block the work by itself.

| Work type | Use these skills |
|-----------|------------------|
| Multi-step planning | `writing-plans`, `grill-with-docs` |
| GitOps or cluster integration | `homelab-gitops-operations`, `homelab-kubernetes-operations` |
| n8n import/export, backups, Postgres safety | `homelab-backup-restore`, `systematic-debugging` |
| Secrets or API tokens | `homelab-secret-management`, `security-review` |
| Completion checks | `verification-before-completion` |

## Arresto e prosecuzione

Fermarsi solo quando il lavoro richiede una decisione non documentata, supera lo scope approvato, viola una fonte `Active`, comporta conseguenze rilevanti non valutate oppure richiede una verifica obbligatoria che resta ineseguibile dopo ragionevoli tentativi.

Prima di fermarsi, indicare la condizione applicabile, il fatto osservato e la decisione o informazione necessaria.

Una condizione di stop si applica al solo perimetro che la richiede. Il blocco di un task, una fase o un'operazione non blocca automaticamente l'intera missione: il lavoro già autorizzato e determinato che non dipende da quella condizione deve proseguire.

Quando la fonte attiva o il task corrente identifica già il lavoro successivo necessario nella stessa missione, proseguire senza chiedere una conferma meccanica, salvo che si applichi una condizione di stop reale.

Non fermarsi per passaggi già approvati, errori locali correggibili, verifiche risolvibili entro lo scope, stato documentale correggibile in modo univoco o fallback già autorizzati.

## Governo, review e template

- Le istruzioni di questo file sono vincolanti; ogni deroga richiede autorizzazione esplicita.
- Ogni review deve indicare la revisione esaminata; se modifiche successive cambiano materialmente la superficie valutata, ripetere review e verifiche pertinenti.
- Ogni testo rivolto a persone deve passare una revisione tecnica e `humanize-writing` quando disponibile, nel rispetto delle regole linguistiche del repository.
- Il template Agent OS è uno scheletro, non una fonte autorevole: non copiarlo né introdurre percorsi, documenti o regole senza un requisito concreto.

## Closeout terminale RFC-0001

Prima del merge terminale, del commit o push che conclude la missione oppure della chiusura dell'issue, completare il closeout previsto da RFC-0001.

Verificare tutte le fonti autorevoli e i documenti `Active` interessati. Aggiornare quelli che mantengono la stessa funzione; archiviare nella stessa modifica quelli conclusi, superati, sostituiti, obsoleti o non più operativi. Prima dell'archiviazione trasferire fatti, decisioni, limiti, requisiti e obblighi di verifica ancora durevoli nella fonte corrente; rimuovere poi il documento da puntatori, indici, tracker, code di lavoro, sezioni sullo stato corrente e istruzioni operative.

I commenti GitHub forniscono tracciabilità, ma non sostituiscono la documentazione autorevole. Quando un'evidenza runtime è un criterio di accettazione, mantenere la missione aperta e non usare `Closes #N` finché tale evidenza manca. `NON APPLICABILE` richiede una motivazione concreta e verificabile.

Commit e push intermedi restano consentiti; quello terminale deve includere il closeout completato.

## Commit Style

Use Conventional Commits, for example:

```text
docs: add n8n workflow import handoff
feat(workflows): add daily report workflow
chore(validation): add workflow JSON checks
```

## Repository intelligence

Use GitNexus when it is available and materially reduces uncertainty about unfamiliar flows or a broad blast radius. Direct source inspection, caller analysis, focused tests, and equivalent tools remain valid evidence; GitNexus is not a universal prerequisite for editing or committing.
