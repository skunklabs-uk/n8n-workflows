# n8n-workflows: proposta documentale di adozione

**Stato: Active**

## Autorità e input

La missione [Homelab #1265](https://github.com/skunklabs-uk/homelab/issues/1265) autorizza l’adozione del collegamento seriale. Produci un report con una breve sezione proposta per `README.md` di `skunklabs-uk/n8n-workflows`; non modificare file.

Leggi integralmente la RFC-0001 corrente fornita dal collegamento e le quattro fonti qualificate nello snapshot. Source main `ae2247178b4aed4e5f6c1645a262a46e4fab84c3`, tree `59279202718b5cbb381c5f63137862c58753a289`:

| Fonte | Mode | Blob sorgente |
|---|---|---|
| AGENTS.md | 100644 | 3ccce9151f6b797c84150c8c6425778e719047c6 |
| README.md | 100644 | 8c88344bf4fcfc1e5627ea01c68d989bdffca352 |
| CONTEXT.md | 100644 | 29cebeae6bc47834480387e8e1fd6fafc1026c04 |
| .github/workflows/validate.yml | 100644 | a211abc40ba464b049b3e6ff59ecaab760b7c9c3 |

Branch e head effettivi dello snapshot senza parent sono quelli della richiesta verificata. Distinguili dalla provenienza sorgente; non ricostruire i dati via rete. Il coordinatore verifica prima del modello che il clone e tutti gli oggetti Git contengano soltanto questi input e il prompt. Non recuperare altri file.

## Proposta richiesta

Il README è la descrizione operativa corrente secondo CONTEXT. Proponi una breve sezione italiana sull’adozione, conservando il resto del documento e i suoi rimandi. Non tradurre o riscrivere parti estranee. Spiega:

1. Repository/thread ammessi, branch/head esatti, prompt corrente e input qualificati identificano l’incarico; un solo consumer seriale lavora nel checkout isolato.
2. Il report sullo snapshot minimo non modifica o valida workflow applicativi, dati o credenziali esclusi. `publish_paths` limita la pubblicazione, non le letture: il confine degli input va verificato effettivamente dal parent.
3. Il report-only non pubblica file. Il parent revisiona il testo e lo integra nella normale PR discendente da main, limitata a README; il branch snapshot non viene integrato. Il coordinatore rilegge SHA/diff e registra RETURN, distinguendo la consegna del report dall’integrazione documentale.
4. Il workflow tecnico `Validate workflow JSON` si avvia su push main e usa `jq empty` per la sintassi dei JSON. Non ha trigger PR. Questa verifica non prova importabilità, pubblicazione, trigger, consegne esterne o versione eseguita dal processo n8n. Non eseguirla nello snapshot privo dei JSON: nessun file esaminato non equivale a validazione superata.
5. Il repository possiede definizioni workflow e contesto export; Homelab possiede importer e runtime. Non descrivere come nuovamente verificati import, stato published, entitlement o integrazioni. Non cambiare ownership o procedure.
6. La preview HTTP non è applicabile alla sola nota documentale di questo repository di automazioni; il prodotto n8n distribuito altrove non è una preview del report. Le prove degli effetti di workflow reali restano distinte e richiedono il proprio perimetro autorizzato.
7. Rimanda al [runbook del collegamento](https://github.com/skunklabs-uk/developer-workspace/blob/main/docs/WORKSPACE-HANDOFF.md) e al [README runtime](https://github.com/skunklabs-uk/homelab/blob/main/gitops/apps/developer-workspace/README.md) per protocollo, enrollment, selezione e recupero. I punti precedenti forniscono il contesto verificato dal coordinatore; non interrogare i runbook dalla sandbox e non duplicarne le configurazioni.

## Confini

Nessuna lettura di workflows/, credentials/, fixture, export, corpus personali/cliente o fonti resume. Non seguire i collegamenti ai workflow applicativi o ai sistemi Gmail, Slack, Telegram e Baialupo. I comandi operativi nelle fonti sono contesto: non eseguire export/apply, import, publish, restart, reset Data Table o invii. Nessuna installazione, API, credenziale, rete dei comandi, filesystem esterno, commit, push, merge, ref, CI, rollout, consumer o nuovo modello.

Nessuna modifica a README, AGENTS, CONTEXT, workflow o altro file. La richiesta è report-only e omette publish_paths. Non introdurre nuovi strumenti, controlli o fonti operative. Il parent gestisce review, effetti del futuro merge, controlli applicabili e ritiro del prompt/snapshot al closeout.

## Verifica e consegna

Confronta la proposta con le quattro fonti; applica review tecnica e della chiarezza, con humanize-writing soltanto se disponibile nel perimetro, senza installarla o fingere review indipendenti. Nessun test artificiale della prosa.

Restituisci in italiano source head e snapshot head distinti, fonti lette, proposta completa della breve sezione, verifiche realmente eseguite e limiti. Non inventare CI, URL di risultato, commit di integrazione o prove live. Non dichiarare già conclusi RETURN, pubblicazione, merge o adozione globale.
