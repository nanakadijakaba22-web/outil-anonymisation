// tools/generate-raw-clients.js
// Usage: node tools/generate-raw-clients.js <nb_lignes> <chemin_sortie.csv>
// Ex:    node tools/generate-raw-clients.js 1000000 .\data\clients-raw-1M.csv
// Données 100% SYNTHÉTIQUES (pas de vraies personnes).

const fs = require("fs");
const path = require("path");

// --------- CLI ---------
const N = parseInt(process.argv[2] || "1000000", 10);
const out = process.argv[3] || path.join("data", "clients-raw.csv");
fs.mkdirSync(path.dirname(out), { recursive: true });

// --------- Stream sortie ---------
const ws = fs.createWriteStream(out, { encoding: "utf8" });
ws.write("\uFEFF"); // BOM UTF-8 pour Excel
ws.write("id_client,prenom,nom,email,telephone,adresse,ville,province,code_postal,date_naissance,revenu_annuel\n");

// --------- RNG déterministe (xorshift) ---------
function rng(seed = 123456789) {
  let x = seed >>> 0;
  return () => {
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
    return (x >>> 0) / 4294967296;
  };
}
const rnd = rng(42);
function rint(a, b) { return Math.floor(rnd() * (b - a + 1)) + a; }
function pick(arr) { return arr[rint(0, arr.length - 1)]; }

// --------- Petits vocabulaires QC/CA ---------
const firstNames = ["Nora","Emma","Léa","Olivia","Mila","Élise","Liam","William","Noah","Thomas","Raphaël","Émile","Zoe","Ava","Élodie","Antoine","Mathis","Jacob","Ethan","Adam"];
const lastNames  = ["Tremblay","Gagnon","Roy","Côté","Bouchard","Gauthier","Morin","Lavoie","Fortin","Gagné","Ouellet","Pelletier","Bélanger","Lefebvre","Martel","Richard","Poirier","Deschamps","Boucher","Carpentier"];
const streetNames= ["St-Denis","Sherbrooke","Ste-Catherine","Papineau","Mont-Royal","Laurier","Bourassa","Masson","Viau","Belmont","Victoria","King","Main","St-Jean","Grande-Allée","Cartier","Racine","Frontenac","Dollard","Beaubien"];
const streetTypes= ["Rue","Avenue","Boulevard","Chemin","Place"];
const villesQC   = ["Montréal","Québec","Laval","Gatineau","Longueuil","Sherbrooke","Saguenay","Lévis","Trois-Rivières","Terrebonne","Brossard","Repentigny","Drummondville","Saint-Jérôme","Granby","Blainville","Saint-Jean-sur-Richelieu","Shawinigan","Chicoutimi","Rimouski"];
const indicatifs = [514,438,450,579,581,418,819,873,367];

// FSA québécoise (G,H,J) + schéma A1A1A1
const letters = "ABCEGHJKLMNPRSTVXY";
function fsaQC() { return ["G","H","J"][rint(0,2)] + rint(0,9) + letters[rint(0,letters.length-1)]; }
function codePostal() { return fsaQC() + rint(0,9) + letters[rint(0,letters.length-1)] + rint(0,9); }

function dateNaissance() {
  const y = rint(1940, 2005);
  const m = rint(1, 12);
  const leap = (y%4===0 && (y%100!==0 || y%400===0)) ? 1 : 0;
  const mdays = [31,28+leap,31,30,31,30,31,31,30,31,30,31][m-1];
  const d = rint(1, mdays);
  return `${y}-${String(m).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
}

function revenuAnnuel() {
  const r = rnd();
  if (r < 0.25) return rint(22000, 39999);
  if (r < 0.55) return rint(40000, 59999);
  if (r < 0.85) return rint(60000, 79999);
  if (r < 0.97) return rint(80000, 119999);
  return rint(120000, 200000);
}

function telephone() {
  const a = pick(indicatifs);
  const b = rint(200, 999);
  const c = rint(1000, 9999);
  return `${a}-${b}-${c}`;
}

function adresse() {
  const no = rint(10, 9999);
  const st = pick(streetNames);
  const tp = pick(streetTypes);
  return `${no} ${tp} ${st}`;
}

let i = 0;
const t0 = Date.now();

function write() {
  let ok = true;
  while (i < N && ok) {
    i++;
    const prenom = pick(firstNames);
    const nom    = pick(lastNames);
    const ville  = pick(villesQC);
    const email  = `${prenom}.${nom}.${i}@bnc.example`.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"");
    const line = [
      i, prenom, nom, email, telephone(),
      adresse(), ville, "QC", codePostal(), dateNaissance(), revenuAnnuel()
    ].join(",") + "\n";
    ok = ws.write(line);
    if (i % 100000 === 0) process.stdout.write(`\r${i.toLocaleString()} / ${N.toLocaleString()} lignes...`);
  }
  if (i < N) ws.once("drain", write);
  else ws.end(() => {
    const dt = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`\n✅ Fini: ${N.toLocaleString()} lignes -> ${out} (${dt}s)`);
  });
}
write();
