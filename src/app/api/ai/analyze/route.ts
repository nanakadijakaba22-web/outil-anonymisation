import { NextResponse } from "next/server";

const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL ?? "llama3.1:8b";

type TypeSensibilite =
  | "IDENTIFIANT_DIRECT"
  | "QUASI_IDENTIFIANT"
  | "DONNEE_SENSIBLE"
  | "NON_SENSIBLE";

type Niveau = "faible" | "moyen" | "fort";

function normalize(s: string) {
  return (s ?? "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/**
 * Règles minimales "verrou" pour éviter les erreurs grossières.
 * On ne force que les cas évidents. Le reste est laissé à Ollama.
 */
function forcedClassification(colName: string): { type: TypeSensibilite; sensitivity: Niveau } | null {
  const n = normalize(colName);

  // Identifiants directs évidents
  const directKeys = [
    "email", "e-mail", "mail",
    "telephone", "tel", "phone",
    "nas", "ssn", "assurance sociale",
    "iban", "swift",
    "numero_compte", "num_compte", "account_number", "account",
    "numero_carte", "carte", "card",
    "id_client", "client_id",
    "adresse", "rue", "code_postal", // (adresse complète -> direct; code_postal seul -> plutôt quasi, mais on ne force que si "adresse")
  ];

  // Données sensibles évidentes (santé + autres sensibles)
  const sensitiveKeys = [
    "diagnostic", "maladie", "pathologie", "symptome",
    "medicament", "traitement",
    "sante", "hopital", "clinique",
    "biometr", "empreinte", "iris",
  ];

  // Force direct si correspondances très fortes
  if (
    directKeys.some((k) => n.includes(k)) &&
    (n.includes("email") ||
      n.includes("telephone") ||
      n.includes("nas") ||
      n.includes("ssn") ||
      n.includes("iban") ||
      n.includes("numero_compte") ||
      n.includes("account_number") ||
      n.includes("numero_carte") ||
      n.includes("id_client") ||
      n.includes("adresse"))
  ) {
    return { type: "IDENTIFIANT_DIRECT", sensitivity: "fort" };
  }

  // Force sensible si correspondances santé/biométrie
  if (sensitiveKeys.some((k) => n.includes(k))) {
    return { type: "DONNEE_SENSIBLE", sensitivity: "fort" };
  }

  return null;
}

function mapTypeToSensitivity(t: TypeSensibilite): Niveau {
  switch (t) {
    case "IDENTIFIANT_DIRECT":
    case "DONNEE_SENSIBLE":
      return "fort";
    case "QUASI_IDENTIFIANT":
      return "moyen";
    case "NON_SENSIBLE":
    default:
      return "faible";
  }
}

export async function POST(req: Request) {
  try {
    const { datasetName, columns } = await req.json();

    if (!Array.isArray(columns) || columns.length === 0) {
      return NextResponse.json({ error: "Missing columns" }, { status: 400 });
    }

    // 1) Pré-classement (verrou) pour éviter les incohérences
    const forced: any[] = [];
    const toAI: any[] = [];

    for (const c of columns) {
      const name = c?.name ?? c?.column ?? "";
      const sampleValues = Array.isArray(c?.sampleValues) ? c.sampleValues : [];
      const locked = forcedClassification(name);

      if (locked) {
        forced.push({
          name,
          type: locked.type,
          sensitivity: locked.sensitivity,
          confidence: 1.0,
          // le reste sera complété par la UI ou par un prompt secondaire si vous voulez
          category: "AUTRE",
          risks: {
            correlation: { score: 0, level: "faible" },
            individuation: { score: 0, level: "faible" },
            inference: { score: 0, level: "faible" },
          },
          recommended_actions: [],
          justification: `Règle déterministe: ${locked.type} → sensibilité ${locked.sensitivity}.`,
          _forced: true,
        });
      } else {
        toAI.push({ name, sampleValues });
      }
    }

    // 2) Si tout est forcé, on renvoie directement
    if (toAI.length === 0) {
      return NextResponse.json({
        columns: forced,
        overall: {
          risk_level: "moyen",
          top_risks: [],
          global_justification: "Classification déterministe appliquée aux colonnes évidentes.",
        },
      });
    }

    // 3) Prompt Ollama : classification complète + justification + risques
    const prompt = `
Tu es un expert en anonymisation conforme au règlement québécois (corrélation, individuation, inférence).
Retourne UNIQUEMENT un JSON valide, sans texte autour.

Définitions (OBLIGATOIRES):
- IDENTIFIANT_DIRECT: identifie directement une personne (nom, prénom, email, téléphone, numéro de compte, NAS, etc.)
- QUASI_IDENTIFIANT: n'identifie pas seul, mais peut identifier en combinaison (âge/date_naissance, code postal, ville, sexe, profession, etc.)
- DONNEE_SENSIBLE: santé, biométrie, informations hautement sensibles
- NON_SENSIBLE: technique ou général non personnel (status générique, catégorie produit, logs non rattachés, etc.)

Règle absolue:
- Tout "numéro de compte / IBAN / numéro carte / NAS / email / téléphone" doit être classé IDENTIFIANT_DIRECT et sensibilité fort.
- Toute santé/biométrie doit être DONNEE_SENSIBLE et sensibilité fort.

Sensibilité:
- fort pour IDENTIFIANT_DIRECT et DONNEE_SENSIBLE
- moyen pour QUASI_IDENTIFIANT (peut être fort si très identifiant)
- faible pour NON_SENSIBLE

DATASET: ${datasetName ?? "unknown"}

COLONNES (nom + exemples):
${toAI
  .map((c: any) => `- ${c.name}: ${(c.sampleValues ?? []).slice(0, 8).join(", ") || "(no samples)"}`)
  .join("\n")}

TÂCHES:
1) Pour chaque colonne: choisir type ∈ {IDENTIFIANT_DIRECT, QUASI_IDENTIFIANT, DONNEE_SENSIBLE, NON_SENSIBLE}
2) Donner sensitivity ∈ {faible, moyen, fort} selon les règles
3) Donner confidence ∈ [0,1]
4) Évaluer 3 risques: correlation, individuation, inference (score 0-100 + level faible/moyen/fort)
5) Donner recommended_actions (liste courte)
6) Donner justification (1-3 phrases) qui cite au moins un indice (nom, format, exemples, unicité probable)

SORTIE JSON attendue:
{
  "columns": [
    {
      "name": "string",
      "type": "IDENTIFIANT_DIRECT|QUASI_IDENTIFIANT|DONNEE_SENSIBLE|NON_SENSIBLE",
      "sensitivity": "faible|moyen|fort",
      "confidence": 0.0,
      "category": "RP|FINANCE|SANTE|ASSURANCE|AUTRE",
      "risks": {
        "correlation": {"score": 0, "level": "faible|moyen|fort"},
        "individuation": {"score": 0, "level": "faible|moyen|fort"},
        "inference": {"score": 0, "level": "faible|moyen|fort"}
      },
      "recommended_actions": ["string"],
      "justification": "string"
    }
  ],
  "overall": {
    "risk_level": "faible|moyen|fort",
    "top_risks": ["correlation|individuation|inference"],
    "global_justification": "string"
  }
}
`;

    const r = await fetch(`${OLLAMA_URL}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: OLLAMA_MODEL, prompt, stream: false }),
    });

    if (!r.ok) {
      return NextResponse.json(
        { error: "Ollama failed", details: await r.text() },
        { status: 500 }
      );
    }

    const data = await r.json();
    const raw = String(data?.response ?? "").trim();

    const a = raw.indexOf("{");
    const b = raw.lastIndexOf("}");
    if (a < 0 || b < 0) {
      return NextResponse.json({ error: "No JSON returned", raw }, { status: 500 });
    }

    const parsed = JSON.parse(raw.slice(a, b + 1));

    // 4) Post-traitement : garantir cohérence type ↔ sensibilité
    const aiCols = (parsed.columns ?? []).map((c: any) => {
      const t = c.type as TypeSensibilite;
      if (t && !c.sensitivity) c.sensitivity = mapTypeToSensitivity(t);
      if (t === "IDENTIFIANT_DIRECT" || t === "DONNEE_SENSIBLE") c.sensitivity = "fort";
      return c;
    });

    return NextResponse.json({
      columns: [...forced, ...aiCols],
      overall: parsed.overall ?? {
        risk_level: "moyen",
        top_risks: [],
        global_justification: "Résumé non fourni.",
      },
    });
  } catch (e: any) {
    return NextResponse.json(
      { error: "Server error", details: String(e?.message ?? e) },
      { status: 500 }
    );
  }
}
