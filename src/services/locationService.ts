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

export const locationService = {
  async getWoredasForRegion(regionName: string): Promise<string[]> {
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
    const names = woredas
      .filter((woreda) => zoneIds.has(String(woreda.parent_id ?? '')))
      .map((woreda) => (woreda.name_en || woreda.name_local || '').trim())
      .filter(Boolean);
    return [...new Set(names)].sort((a, b) => a.localeCompare(b));
  },
};
