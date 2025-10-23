// tools/anonymize-csv.js
// Usage: node tools/anonymize-csv.js input.csv [output.csv]
// Définis un sel: HASH_SALT (ex: set "HASH_SALT=xxx" && node ...)

const fs = require("fs");
const crypto = require("crypto");
const { parse } = require("csv-parse");
const { format } = require("fast-csv");

const input = process.argv[2];
const output =
  process.argv[3] ||
  (input ? input.replace(/\.csv$/i, "") + "-anon.csv" : null);

if (!input || !output) {
  console.error("Usage: node tools/anonymize-csv.js <input.csv> [output.csv]");
  process.exit(1);
}

const SALT = process.env.HASH_SALT || "change-me-salt";

// Détecte le séparateur (',' ';' ou tab)
async function detectDelimiter(path) {
  return await new Promise((resolve, reject) => {
    const rs = fs.createReadStream(path, { encoding: "utf8", highWaterMark: 64 * 1024 });
    let chunk = "";
    rs.on("data", (d) => { chunk += d; rs.close(); });
    rs.on("close", () => {
      const header = (chunk.split(/\r?\n/)[0] || "").replace(/^\uFEFF/, "");
      const counts = {
        ",": (header.match(/,/g) || []).length,
        ";": (header.match(/;/g) || []).length,
        "\t": (header.match(/\t/g) || []).length,
      };
      const delim = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || ",";
      resolve(delim);
    });
    rs.on("error", reject);
  });
}

function hmac(val) {
  if (val == null) return val;
  return crypto.createHmac("sha256", SALT).update(String(val)).digest("hex").slice(0, 12);
}

// ⚠️ adapte les noms de colonnes à ton schéma
function generalizeRow(row) {
  if (row.id_client) row.id_client = hmac(row.id_client);                  // pseudonymisation
  if (row.date_naissance) row.date_naissance = String(row.date_naissance).slice(0, 4); // année
  if (row.code_postal) row.code_postal = String(row.code_postal).slice(0, 3) + "***";  // FSA
  if (row.revenu_annuel) {
    const n = Number(String(row.revenu_annuel).replace(/[^0-9.]/g, ""));
    if (!Number.isNaN(n)) {
      // libellés ASCII pour éviter les soucis d'encodage dans Excel
      row.revenu_annuel =
        n < 40000 ? "<40k" :
        n < 60000 ? "40-60k" :
        n < 80000 ? "60-80k" :
                    ">=80k";
    }
  }
  return row;
}

(async () => {
  try {
    const delimiter = await detectDelimiter(input);
    console.log(`➡️  Lecture: ${input}`);
    console.log(`   Délimiteur: ${JSON.stringify(delimiter)}`);
    console.log(`   Sortie: ${output}`);

    const read = fs.createReadStream(input);
    const parser = parse({
      columns: true,
      delimiter,
      bom: true,
      skip_empty_lines: true,
      relax_column_count: true,
    });

    const formatter = format({ headers: true });

    // BOM UTF-8 pour que Excel détecte correctement l'encodage
    const write = fs.createWriteStream(output, { encoding: "utf8" });
    write.write("\uFEFF");

    let n = 0;
    const t0 = Date.now();

    parser.on("data", (row) => {
      n++;
      formatter.write(generalizeRow(row));
      if (n % 100000 === 0) {
        const dt = ((Date.now() - t0) / 1000).toFixed(1);
        console.log(`   ${n.toLocaleString()} lignes traitées (${dt}s)`);
      }
    });

    parser.on("end", () => formatter.end());
    parser.on("error", (e) => { console.error("❌ Erreur parse:", e); process.exit(1); });

    formatter.on("finish", () => {
      const dt = ((Date.now() - t0) / 1000).toFixed(1);
      console.log(`✅ Terminé: ${n.toLocaleString()} lignes en ${dt}s`);
      console.log(`   Fichier: ${output}`);
    });

    read.pipe(parser);
    formatter.pipe(write);
  } catch (e) {
    console.error("❌ Erreur:", e);
    process.exit(1);
  }
})();
