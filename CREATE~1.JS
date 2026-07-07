/**
 * Generates the Engine Wiring Inspection Problem Statement as a Word document.
 *
 * Run:
 *   npm install -g docx
 *   node create_problem_statement.js
 */

const {
    Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
    Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
    ShadingType, PageNumber, LevelFormat, VerticalAlign
} = require("docx");
const fs = require("fs");

// ── Helpers ────────────────────────────────────────────────────────────────

const BLUE       = "1F4E79";
const LIGHT_BLUE = "D6E4F0";
const MID_BLUE   = "2E75B6";
const WHITE      = "FFFFFF";
const DARK_GRAY  = "404040";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function heading1(text) {
    return new Paragraph({
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 320, after: 160 },
        children: [new TextRun({ text, bold: true, size: 32, color: BLUE, font: "Arial" })],
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_BLUE, space: 4 } },
    });
}

function heading2(text) {
    return new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 240, after: 120 },
        children: [new TextRun({ text, bold: true, size: 26, color: MID_BLUE, font: "Arial" })],
    });
}

function body(text, opts = {}) {
    return new Paragraph({
        spacing: { before: 80, after: 100 },
        children: [new TextRun({
            text,
            size: 22,
            font: "Arial",
            color: DARK_GRAY,
            bold: opts.bold || false,
            italics: opts.italic || false,
        })],
        alignment: opts.justify ? AlignmentType.JUSTIFIED : AlignmentType.LEFT,
    });
}

function bullet(text, bold_prefix = "") {
    return new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        spacing: { before: 60, after: 60 },
        children: [
            bold_prefix ? new TextRun({ text: bold_prefix, bold: true, size: 22, font: "Arial", color: DARK_GRAY }) : null,
            new TextRun({ text, size: 22, font: "Arial", color: DARK_GRAY }),
        ].filter(Boolean),
    });
}

function spacer() {
    return new Paragraph({ spacing: { before: 100, after: 100 }, children: [new TextRun("")] });
}

function callout(text) {
    return new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [9360],
        rows: [new TableRow({
            children: [new TableCell({
                borders,
                width: { size: 9360, type: WidthType.DXA },
                shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR },
                margins: { top: 160, bottom: 160, left: 240, right: 240 },
                children: [new Paragraph({
                    children: [new TextRun({ text, size: 22, font: "Arial", color: BLUE, italics: true })],
                    alignment: AlignmentType.JUSTIFIED,
                })],
            })],
        })],
    });
}

function twoColRow(label, value, shade) {
    return new TableRow({
        children: [
            new TableCell({
                borders,
                width: { size: 3120, type: WidthType.DXA },
                shading: { fill: shade ? "1F4E79" : "2E75B6", type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 160, right: 160 },
                verticalAlign: VerticalAlign.CENTER,
                children: [new Paragraph({
                    children: [new TextRun({ text: label, bold: true, size: 20, font: "Arial", color: WHITE })],
                })],
            }),
            new TableCell({
                borders,
                width: { size: 6240, type: WidthType.DXA },
                shading: { fill: shade ? "EBF3FB" : "F5F9FD", type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 160, right: 160 },
                children: [new Paragraph({
                    children: [new TextRun({ text: value, size: 20, font: "Arial", color: DARK_GRAY })],
                })],
            }),
        ],
    });
}

// ── Document ───────────────────────────────────────────────────────────────

const doc = new Document({
    numbering: {
        config: [
            {
                reference: "bullets",
                levels: [{
                    level: 0, format: LevelFormat.BULLET, text: "•",
                    alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } },
                }],
            },
        ],
    },
    styles: {
        default: { document: { run: { font: "Arial", size: 22 } } },
        paragraphStyles: [
            {
                id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
                run: { size: 32, bold: true, font: "Arial", color: BLUE },
                paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 },
            },
            {
                id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal",
                run: { size: 26, bold: true, font: "Arial", color: MID_BLUE },
                paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 },
            },
        ],
    },
    sections: [{
        properties: {
            page: {
                size: { width: 12240, height: 15840 },
                margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
            },
        },
        headers: {
            default: new Header({
                children: [new Paragraph({
                    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: MID_BLUE, space: 4 } },
                    children: [
                        new TextRun({ text: "Engine Wiring Inspection  |  Solution Accelerator", size: 18, font: "Arial", color: MID_BLUE }),
                    ],
                })],
            }),
        },
        footers: {
            default: new Footer({
                children: [new Paragraph({
                    border: { top: { style: BorderStyle.SINGLE, size: 4, color: MID_BLUE, space: 4 } },
                    alignment: AlignmentType.RIGHT,
                    children: [
                        new TextRun({ text: "Page ", size: 18, font: "Arial", color: DARK_GRAY }),
                        new TextRun({ children: [PageNumber.CURRENT], size: 18, font: "Arial", color: DARK_GRAY }),
                        new TextRun({ text: " of ", size: 18, font: "Arial", color: DARK_GRAY }),
                        new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, font: "Arial", color: DARK_GRAY }),
                    ],
                })],
            }),
        },
        children: [

            // ── Cover ──────────────────────────────────────────────────
            new Paragraph({
                spacing: { before: 1440, after: 240 },
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "PROBLEM STATEMENT", size: 52, bold: true, font: "Arial", color: BLUE })],
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 0, after: 120 },
                children: [new TextRun({ text: "Engine Wiring Visual Inspection", size: 40, bold: true, font: "Arial", color: MID_BLUE })],
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 0, after: 480 },
                children: [new TextRun({ text: "AI-Powered Solution Accelerator", size: 28, font: "Arial", color: DARK_GRAY, italics: true })],
            }),

            // Metadata table
            new Table({
                width: { size: 7200, type: WidthType.DXA },
                columnWidths: [3120, 4080],
                rows: [
                    twoColRow("Document Type",    "Problem Statement",             false),
                    twoColRow("Domain",           "Automotive Manufacturing QA",   true),
                    twoColRow("Component",        "Engine Wiring Assembly",        false),
                    twoColRow("Solution Type",    "AI + Computer Vision",          true),
                    twoColRow("Version",          "1.0",                           false),
                ],
            }),

            spacer(),
            spacer(),

            // ── 1. Background ──────────────────────────────────────────
            heading1("1.  Background"),
            body(
                "In automotive manufacturing, engine wiring assemblies are among the most " +
                "safety-critical components in a vehicle. Proper assembly and containment of " +
                "engine wiring ensures reliable electrical signal transmission, prevents " +
                "vibration-induced failures, and protects wires from heat and mechanical damage " +
                "during the operational life of the vehicle.",
                { justify: true }
            ),
            spacer(),
            body(
                "Each engine wiring assembly must conform to a precise configuration: a bundle " +
                "of coloured wires (orange, yellow, green) must be held together by a blue retention " +
                "hoop, which in turn must be secured between two metal clips fastened to the engine " +
                "structure. This specific arrangement ensures the wiring harness remains correctly " +
                "routed, mechanically stable, and protected from engine vibration throughout the " +
                "vehicle lifecycle.",
                { justify: true }
            ),
            spacer(),

            // ── 2. Problem Statement ───────────────────────────────────
            heading1("2.  Problem Statement"),
            callout(
                "\"Automotive manufacturers currently rely on manual visual inspection to verify " +
                "engine wiring assembly correctness. This process is slow, inconsistent, and " +
                "error-prone — allowing defective assemblies to pass through to final vehicle " +
                "build, creating downstream safety, warranty, and recall risks.\""
            ),
            spacer(),
            body(
                "Specifically, the inspection must verify three structural conditions that are " +
                "difficult for human inspectors to assess consistently at production line speeds:",
                { justify: true }
            ),
            spacer(),
            bullet("The blue retention hoop is present in the assembly.", "Hoop Presence:  "),
            bullet("Two metal clips are correctly fastened over the wire bundle.", "Clip Presence:  "),
            bullet("The blue hoop is positioned between the two clips — not displaced to either side.", "Hoop Position:  "),
            spacer(),
            body(
                "Additionally, any surface defects, wire damage, or assembly anomalies that deviate " +
                "from the expected normal appearance must be detected and flagged for rework before " +
                "the assembly progresses to the next stage of vehicle build.",
                { justify: true }
            ),
            spacer(),

            // ── 3. Challenges ──────────────────────────────────────────
            heading1("3.  Challenges with Manual Inspection"),

            heading2("3.1  Inconsistency and Human Error"),
            body(
                "Manual visual inspection is inherently subjective. Inspector fatigue, lighting " +
                "variation on the production floor, and individual differences in attention and " +
                "experience lead to inconsistent defect detection rates. Studies in automotive " +
                "quality control consistently show that manual inspection achieves detection rates " +
                "of only 60-80% for subtle assembly defects.",
                { justify: true }
            ),

            heading2("3.2  Production Line Speed"),
            body(
                "Modern automotive assembly lines operate at high throughput. Manual inspection " +
                "creates a bottleneck at quality gate stations, either slowing the line or forcing " +
                "inspectors to make rapid assessments that increase the risk of missed defects. " +
                "There is a fundamental tension between inspection thoroughness and production speed " +
                "that cannot be resolved by manual processes alone.",
                { justify: true }
            ),

            heading2("3.3  Subtle and Compound Defects"),
            body(
                "Engine wiring defects are often visually subtle. A displaced blue hoop may be " +
                "only a few millimetres out of position. Wire insulation damage may present as a " +
                "small surface discolouration. A missing clip may be obscured by other components. " +
                "These defects require close, focused inspection that is difficult to sustain " +
                "consistently across an entire production shift.",
                { justify: true }
            ),

            heading2("3.4  No Audit Trail"),
            body(
                "Manual inspection produces no reliable digital record of each inspection decision. " +
                "This makes it impossible to analyse defect trends, identify recurring assembly " +
                "problems, correlate defects with specific production shifts or operators, or " +
                "demonstrate regulatory compliance for quality audits.",
                { justify: true }
            ),
            spacer(),

            // ── 4. Consequences ────────────────────────────────────────
            heading1("4.  Consequences of Missed Defects"),

            heading2("4.1  Safety Risk"),
            body(
                "Engine wiring containment failures that reach the field can cause serious safety " +
                "incidents. Uncontained wires are exposed to engine heat, vibration, and contact " +
                "with moving parts — leading to insulation failure, short circuits, and in extreme " +
                "cases engine fires. A missing blue hoop or clip means the wire bundle is no longer " +
                "routed safely, increasing the risk of contact with exhaust surfaces and rotating components.",
                { justify: true }
            ),

            heading2("4.2  Warranty and Recall Cost"),
            body(
                "Electrical faults caused by wiring assembly defects are among the highest-cost " +
                "warranty claims in automotive manufacturing. A field recall for a wiring harness " +
                "defect affecting multiple vehicles can cost tens of millions of dollars in parts, " +
                "labour, logistics, and brand damage — far exceeding the cost of preventing the " +
                "defect at the assembly stage.",
                { justify: true }
            ),

            heading2("4.3  Vehicle Performance Degradation"),
            body(
                "Before causing complete failure, loose wiring creates intermittent electrical " +
                "faults — sensor signal noise, ECU error codes, and unreliable operation of " +
                "safety-critical systems including ABS, traction control, and engine management. " +
                "These faults are difficult to diagnose in the field and erode customer confidence.",
                { justify: true }
            ),
            spacer(),

            // ── 5. Proposed Solution ───────────────────────────────────
            heading1("5.  Proposed Solution"),
            body(
                "This solution accelerator delivers an AI-powered visual inspection system " +
                "specifically designed for engine wiring assembly verification. It combines two " +
                "complementary inspection approaches:",
                { justify: true }
            ),
            spacer(),

            new Table({
                width: { size: 9360, type: WidthType.DXA },
                columnWidths: [3120, 6240],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders,
                                width: { size: 3120, type: WidthType.DXA },
                                shading: { fill: BLUE, type: ShadingType.CLEAR },
                                margins: { top: 120, bottom: 120, left: 160, right: 160 },
                                verticalAlign: VerticalAlign.CENTER,
                                children: [new Paragraph({
                                    alignment: AlignmentType.CENTER,
                                    children: [new TextRun({ text: "Inspection Type", bold: true, size: 22, font: "Arial", color: WHITE })],
                                })],
                            }),
                            new TableCell({
                                borders,
                                width: { size: 6240, type: WidthType.DXA },
                                shading: { fill: BLUE, type: ShadingType.CLEAR },
                                margins: { top: 120, bottom: 120, left: 160, right: 160 },
                                children: [new Paragraph({
                                    children: [new TextRun({ text: "What It Detects", bold: true, size: 22, font: "Arial", color: WHITE })],
                                })],
                            }),
                        ],
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders,
                                width: { size: 3120, type: WidthType.DXA },
                                shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR },
                                margins: { top: 100, bottom: 100, left: 160, right: 160 },
                                children: [new Paragraph({
                                    children: [new TextRun({ text: "Anomaly Detection (PatchCore)", bold: true, size: 20, font: "Arial", color: BLUE })],
                                })],
                            }),
                            new TableCell({
                                borders,
                                width: { size: 6240, type: WidthType.DXA },
                                shading: { fill: "F5F9FD", type: ShadingType.CLEAR },
                                margins: { top: 100, bottom: 100, left: 160, right: 160 },
                                children: [new Paragraph({
                                    children: [new TextRun({
                                        text: "Surface defects, wire damage, insulation anomalies, " +
                                              "unusual textures or appearances that deviate from normal " +
                                              "trained on good assemblies only — no defect labels required.",
                                        size: 20, font: "Arial", color: DARK_GRAY,
                                    })],
                                })],
                            }),
                        ],
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders,
                                width: { size: 3120, type: WidthType.DXA },
                                shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR },
                                margins: { top: 100, bottom: 100, left: 160, right: 160 },
                                children: [new Paragraph({
                                    children: [new TextRun({ text: "Structural Inspection (Rule-Based CV)", bold: true, size: 20, font: "Arial", color: BLUE })],
                                })],
                            }),
                            new TableCell({
                                borders,
                                width: { size: 6240, type: WidthType.DXA },
                                shading: { fill: "F5F9FD", type: ShadingType.CLEAR },
                                margins: { top: 100, bottom: 100, left: 160, right: 160 },
                                children: [new Paragraph({
                                    children: [new TextRun({
                                        text: "Missing blue hoop, missing or incorrect number of clips, " +
                                              "blue hoop displaced outside the two clips — " +
                                              "explicit rule-based checks with spatial reasoning.",
                                        size: 20, font: "Arial", color: DARK_GRAY,
                                    })],
                                })],
                            }),
                        ],
                    }),
                ],
            }),

            spacer(),
            body(
                "Both inspection modes operate on a Region of Interest (ROI) selected by the " +
                "quality engineer — focusing computation on the critical assembly area and " +
                "eliminating background noise from surrounding metal structures.",
                { justify: true }
            ),
            spacer(),

            // ── 6. Solution Components ─────────────────────────────────
            heading1("6.  Solution Components"),
            bullet("Data pipeline for loading and preprocessing AutoVI engine wiring images.", "Data Module:  "),
            bullet("PatchCore model with pretrained CNN backbone for unsupervised anomaly detection trained on good images only.", "Anomaly Model:  "),
            bullet("Rule-based structural inspector using HSV colour segmentation and contour analysis to verify hoop and clip presence and position.", "Structural Inspector:  "),
            bullet("Interactive ROI selection tool to define the inspection region on the image.", "ROI Tool:  "),
            bullet("Streamlit web application with two-tab interface for anomaly detection and structural inspection with annotated output images.", "UI:  "),
            bullet("Evaluation pipeline computing image-level AUROC, F1, precision and recall, plus pixel-level AUROC using ground truth masks.", "Evaluation:  "),
            spacer(),

            // ── 7. Expected Benefits ───────────────────────────────────
            heading1("7.  Expected Benefits"),
            bullet("Consistent defect detection independent of operator fatigue, shift, or lighting variation."),
            bullet("Faster inspection throughput — inference runs in seconds per image versus manual inspection."),
            bullet("Digital audit trail — every inspection decision is logged with anomaly score, metrics and annotated image."),
            bullet("Reduced warranty and recall risk by catching assembly defects at source before vehicle build completion."),
            bullet("Scalable to other wiring assembly variants with minimal retraining — only good images required for new categories."),
            bullet("Explainable output — anomaly heatmaps and bounding boxes show inspectors exactly where the defect is located."),
            spacer(),

            // ── 8. Scope ───────────────────────────────────────────────
            heading1("8.  Scope and Limitations"),
            body(
                "This solution accelerator is scoped to the engine wiring assembly inspection task " +
                "using the AutoVI dataset. The structural inspection module is specifically designed " +
                "for the blue hoop and two-clip configuration described in this document. Extension " +
                "to other assembly configurations will require tuning of colour thresholds and " +
                "spatial rules for the new component geometry.",
                { justify: true }
            ),
            spacer(),
            body(
                "The anomaly detection model requires a minimum of 200-300 good training images " +
                "per category to build a representative memory bank. Performance on rare or " +
                "previously unseen defect types depends on the visual distinctiveness of the " +
                "defect relative to the normal training distribution.",
                { justify: true }
            ),
            spacer(),

            // ── Closing callout ────────────────────────────────────────
            callout(
                "This solution accelerator provides a production-ready starting point for automated " +
                "engine wiring inspection — combining the flexibility of unsupervised anomaly detection " +
                "with the precision of rule-based structural verification to deliver comprehensive, " +
                "reliable quality assurance at automotive production line speeds."
            ),
        ],
    }],
});

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("Engine_Wiring_Problem_Statement.docx", buffer);
    console.log("Created: Engine_Wiring_Problem_Statement.docx");
});
