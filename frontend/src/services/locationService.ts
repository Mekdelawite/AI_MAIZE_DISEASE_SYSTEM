type AdminDivision = {
  id: string;
  name_en?: string;
  name_local?: string;
  parent_id?: string | null;
};

type EthiopiaAdminData = {
  regions: AdminDivision[];
  zones: AdminDivision[];
  woredas: AdminDivision[];
};

export type WoredaOption = { value: string; label: string };

const DATA_URL = 'https://api.openadmindata.org/api/v1/et';
let adminDataPromise: Promise<EthiopiaAdminData> | null = null;

async function getLevel(level: 'region' | 'zone' | 'woreda'): Promise<AdminDivision[]> {
  const response = await fetch(`${DATA_URL}/${level}.json`);
  if (!response.ok) {
    throw new Error(`Could not load Ethiopia ${level} data (HTTP ${response.status}).`);
  }
  const payload: any = await response.json();
  const records = payload?.entities ?? payload?.data?.[level] ?? payload?.[level] ?? payload?.data ?? payload;
  if (!Array.isArray(records)) {
    throw new Error(`The Ethiopia ${level} list is unavailable.`);
  }
  return records;
}

function loadEthiopiaAdminData(): Promise<EthiopiaAdminData> {
  if (!adminDataPromise) {
    adminDataPromise = Promise.all([
      getLevel('region'),
      getLevel('zone'),
      getLevel('woreda'),
    ]).then(([regions, zones, woredas]) => ({ regions, zones, woredas }))
      .catch((error) => {
        adminDataPromise = null;
        throw error;
      });
  }
  return adminDataPromise;
}

const normalize = (value: string) => value.trim().toLocaleLowerCase().replace(/[^a-z0-9]+/g, '');

// Open Admin Data's woreda names are mostly written in Latin characters, even
// in its `name_local` field. Provide a readable Amharic-script rendering for
// those names while retaining the canonical English value for account storage.
const FIDEL_ROWS: Record<string, string[]> = {
  h: ['ሀ','ሁ','ሂ','ሃ','ሄ','ህ','ሆ'], l: ['ለ','ሉ','ሊ','ላ','ሌ','ል','ሎ'],
  m: ['መ','ሙ','ሚ','ማ','ሜ','ም','ሞ'], s: ['ሰ','ሱ','ሲ','ሳ','ሴ','ስ','ሶ'],
  r: ['ረ','ሩ','ሪ','ራ','ሬ','ር','ሮ'], q: ['ቀ','ቁ','ቂ','ቃ','ቄ','ቅ','ቆ'],
  b: ['በ','ቡ','ቢ','ባ','ቤ','ብ','ቦ'], t: ['ተ','ቱ','ቲ','ታ','ቴ','ት','ቶ'],
  c: ['ቸ','ቹ','ቺ','ቻ','ቼ','ች','ቾ'], n: ['ነ','ኑ','ኒ','ና','ኔ','ን','ኖ'],
  k: ['ከ','ኩ','ኪ','ካ','ኬ','ክ','ኮ'], w: ['ወ','ዉ','ዊ','ዋ','ዌ','ው','ዎ'],
  z: ['ዘ','ዙ','ዚ','ዛ','ዜ','ዝ','ዞ'], y: ['የ','ዩ','ዪ','ያ','ዬ','ይ','ዮ'],
  d: ['ደ','ዱ','ዲ','ዳ','ዴ','ድ','ዶ'], j: ['ጀ','ጁ','ጂ','ጃ','ጄ','ጅ','ጆ'],
  g: ['ገ','ጉ','ጊ','ጋ','ጌ','ግ','ጎ'], x: ['ጠ','ጡ','ጢ','ጣ','ጤ','ጥ','ጦ'],
  C: ['ጨ','ጩ','ጪ','ጫ','ጬ','ጭ','ጮ'], T: ['ጸ','ጹ','ጺ','ጻ','ጼ','ጽ','ጾ'],
  f: ['ፈ','ፉ','ፊ','ፋ','ፌ','ፍ','ፎ'], p: ['ፐ','ፑ','ፒ','ፓ','ፔ','ፕ','ፖ'],
  v: ['ቨ','ቩ','ቪ','ቫ','ቬ','ቭ','ቮ'],
};
const VOWEL_INDEX: Record<string, number> = { a: 0, u: 1, i: 2, o: 6, e: 4 };
function toAmharicScript(name: string): string {
  if (/[\u1200-\u137F]/.test(name)) return name;
  const text = name.toLowerCase();
  const digraphs: Record<string, string> = { sh: 's', ch: 'c', ny: 'n', ts: 'T', kh: 'h', zh: 'z' };
  let result = '';
  for (let i = 0; i < text.length;) {
    const pair = text.slice(i, i + 2);
    if (digraphs[pair]) { result += FIDEL_ROWS[digraphs[pair]][0]; i += 2; continue; }
    const char = text[i];
    if (char === ' ') { result += ' '; i += 1; continue; }
    if (/[aeiou]/.test(char)) { if (char === 'a' && !result.trim()) result += 'አ'; i += 1; continue; }
    const row = FIDEL_ROWS[char === 't' ? 't' : char === 'c' ? 'c' : char];
    if (!row) { i += 1; continue; }
    const next = text[i + 1];
    if (next === char) {
      const vowelAfterDouble = text[i + 2];
      result += row[VOWEL_INDEX[vowelAfterDouble] ?? 5];
      i += 2;
      if (/[aeiou]/.test(vowelAfterDouble || '')) i += 1;
      continue;
    }
    result += row[VOWEL_INDEX[next] ?? 5];
    i += 1;
    if (/[aeiou]/.test(next || '')) i += 1;
  }
  return result || name;
}

export const locationService = {
  async getWoredasForRegion(regionName: string, language: 'en' | 'am' = 'en'): Promise<WoredaOption[]> {
    const { regions, zones, woredas } = await loadEthiopiaAdminData();
    const region = regions.find((entry) => normalize(entry.name_en || '') === normalize(regionName));
    if (!region) {
      throw new Error(`No Woreda list found for ${regionName}.`);
    }

    const zoneIds = new Set(
      zones
        .filter((zone) => String(zone.parent_id ?? '') === String(region.id))
        .map((zone) => String(zone.id)),
    );
    const options = woredas
      .filter((woreda) => zoneIds.has(String(woreda.parent_id ?? '')))
      .map((woreda) => {
        const value = (woreda.name_en || woreda.name_local || '').trim();
        const localName = (woreda.name_local || '').trim();
        const hasAmharicScript = /[\u1200-\u137F]/.test(localName);
        const label = language === 'am'
          ? hasAmharicScript ? localName : `${toAmharicScript(value)} (${value})`
          : (woreda.name_en || localName || '').trim();
        return { value, label };
      })
      .filter((option) => option.value && option.label);
    return [...new Map(options.map((option) => [option.value, option])).values()]
      .sort((a, b) => a.label.localeCompare(b.label));
  },
};
