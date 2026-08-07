# Guardian Glass — Conversational BI Demo Kit (Medallion Edition)
### Good Data vs Bad Data on a Supplier Scorecard, organised as Silver → Gold

**Prepared for:** EXL Guardian demo team
**Business theme:** Supplier Performance & Scorecard for float-glass raw materials
(silica sand, soda ash, dolomite, limestone, cullet, salt cake, coatings, packaging).

---

## 1. The core idea

The stakeholder wants to *see* how data quality changes what Conversational BI tells them.
We prove it on a **medallion architecture**:

> **Genie / Cortex queries the GOLD layer — but Gold is only as trustworthy as the SILVER events beneath it.**
> Bad Silver silently **propagates** (and amplifies) into Gold aggregates that the chat then reads.

One Genie room, the **same 20 questions**, two datasets:
- **GOOD** → Silver is clean, Gold is correctly derived, answers reconcile.
- **BAD** → 174 defects (130 in Silver, 44 in Gold); the same questions return undercounted,
  contradictory or confidently-wrong answers.

---

## 2. Medallion layers in this kit

| Layer | Role | Tables | Grain |
|---|---|---|---|
| **Bronze** | Raw landing (described, not shipped) | raw ERP/MES/SCADA/WMS extracts | as-ingested |
| **Silver** | Cleaned, conformed **atomic events** + masters | `silver_purchase_order_lines`, `silver_goods_receipts`, `silver_quality_inspections`, `silver_inventory_movements`, `silver_dim_supplier/plant/material/date` | **one row per event** |
| **Gold** | Aggregated **marts the chat queries** | `gold_supplier_scorecard_monthly`, `gold_spend_analysis_monthly`, `gold_inventory_snapshot_monthly`, `gold_demand_supply_monthly`, `gold_supplier_summary` | aggregated (supplier×month, etc.) |

**Gold is genuinely computed from Silver.** In `/good_data`, Silver PO spend and the Gold spend mart
tie to the dollar (**$20,204,896**) — evidence the marts are derived, not hand-made. Inventory Gold is a
**running balance** rolled up from the Silver movement ledger.

---

## 3. What's in the kit

```
Guardian_ConvBI_Demo_Kit/
├── README.md
├── Guardian_ConvBI_Demo_Control_Workbook.xlsx   ← master artifact (7 tabs)
├── genie_room_metadata.yaml                     ← paste-ready room metadata + guardrails (Gold-first)
├── good_data/
│   ├── silver/  (8 files: 4 event tables + 4 conformed masters)
│   └── gold/    (5 aggregated marts)
└── bad_data/
    ├── silver/  (same 8, with Silver defects)
    ├── gold/    (5 marts RE-DERIVED from bad Silver + Gold-only defects)
    └── _defect_log.csv   ← every defect, tagged by layer + recommended catch point
```

**Workbook tabs:** 1) Overview · 2) Medallion Architecture · 3) Data Model (by layer) ·
4) Data Dictionary (by layer, Genie-ready) · 5) Defect Catalogue (layer-tagged) ·
6) Test Questions (20) · 7) Demo Talk Track.

---

## 4. The bad-data defect families (174 defects, layer-tagged)

| Family | What it is | Layer(s) | Why it poisons Conversational BI |
|---|---|---|---|
| **A · Value** | Impossible/out-of-range, wrong units | Silver | KPIs go negative or >100%; aggregations fail or drop rows |
| **B · Orphan keys** | FK with no parent | Silver | Joins drop rows → spend & performance **undercount**; 3-way match fails |
| **C · Missing data** | Nulls in critical/join/group cols | Silver + Gold | OTD uncomputable; "by plant/region" omits rows; averages biased |
| **D · Duplicate + contradictory** | Same key, conflicting facts | Silver + Gold | **Double counting** inflates volumes & averages; "best supplier" wrong |
| **E · Inconsistent encoding** | Categoricals, dates, currency, casing | Silver | Groupings split; time filters misparse; cost comparison invalid |
| **F · Functional / semantic** | Silently-wrong traps | Silver + Gold | The dangerous ones: confident but **wrong** |

**Split:** **Silver 130** (validity, referential integrity, dedup/MDM, unit & currency) ·
**Gold 44** (aggregate duplicates, fraction-vs-percent, a 2nd contradictory rating column, cross-mart disagreement).

**Signature Family-F traps**
- OTD stored as a **fraction (0.98)** mixed with percent → the Gold KPI collapses.
- **Two rating columns** (`supplier_rating` vs `rating_v2`) disagree → "who is preferred?" is ambiguous.
- **Soda Ash movement in KG magnitude** inside an MT column → on-hand explodes.
- **One supplier under two IDs** (SUP-002 / SUP-902) → true spend & performance split in half.
- **Two Gold marts disagree** on spend → reconciliation red flag the chat can't see.

---

## 5. Proof points (measured on the actual files)

| Question | GOOD | BAD |
|---|---|---|
| Silver PO spend = Gold spend mart | **$20,204,896 = $20,204,896** (reconciles) | **$20,186,828 = $20,186,828** (corruption propagated in lockstep) |
| Average OTD % (Gold) | **91.7%** | **84.4%** (fraction/percent mix) |
| Best supplier | **SUP-002 (100.3)** | **SUP-009 at 125.8** — a *poor* supplier, impossible score (dup Gold rows) |
| Scorecard rows | **172** | **179** (double counting) |
| Silver supplier count | **14** | **16** (duplicate + alias entity) |
| Cross-mart spend (summary vs spend mart) | **~$20.2M ≈ $20.2M** | **$21.3M vs $20.2M** (marts disagree) |

---

## 6. How to run the demo

1. **Load `/good_data/gold`** into a Genie/Cortex room; apply `genie_room_metadata.yaml`
   (Gold-first table & column descriptions, synonyms, guardrails). Keep Silver available for drill-down.
2. Ask the **20 questions** (workbook tab 6) — capture correct, reconciled answers.
3. **Point the same room at `/bad_data/gold`** (identical schema).
4. Ask the **same 20 questions** — capture the wrong/broken answers.
5. Open the **Defect Catalogue** (tab 5), **filter by `layer`** to show *where* each defect
   should have been caught (Silver DQ gate / MDM vs Gold model/reconciliation test).
6. Land the EXL message: *Genie/Cortex is the last mile; the governed **Silver → Gold factory**
   beneath it — DQ gates, MDM, conformed metrics, cross-mart reconciliation — is what makes the
   chat trustworthy.*

> Directly answers the internal exec question: *"What happens if we ignore the data foundation and
> plug Genie/Cortex on top of bad data?"* — now quantified, layer by layer.

---

## 7. Consultant's note — optional next steps

- **DQ scorecard slide**: turn the layer-tagged defect log into a completeness / validity /
  uniqueness / referential-integrity heatmap, split by Silver vs Gold.
- **Guardrails A/B**: same question, room *with* vs *without* the metadata instructions.
- **Remediation view**: show the bad → good transformation (dedupe, FK repair, unit & currency
  harmonisation, cross-mart reconciliation) as the EXL "Silver→Gold" value story.
- **Cortex parity**: since Guardian uses Snowflake/Cortex, stage these CSVs as `silver.*` / `gold.*`
  schemas and reproduce the same 20 questions in Cortex Analyst for platform-native credibility.

*All data is synthetic — no real Guardian/Koch figures — but calibrated to be plausible for a
float-glass batch supply chain.*
