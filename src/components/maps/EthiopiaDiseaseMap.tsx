import React, { useEffect, useMemo, useRef, useState } from 'react';

export interface GeoDiagnosis {
  diagnosis_id?: number | string;
  id?: number | string;
  disease_class?: string;
  farmer_name?: string;
  region?: string;
  woreda?: string;
  latitude?: number | string | null;
  longitude?: number | string | null;
  [key: string]: any;
}

interface Props {
  cases: GeoDiagnosis[];
  selectedRegion: string;
  onSelectRegion: (region: string) => void;
}

declare global {
  interface Window { google?: any; __ethiopiaGoogleMapsPromise?: Promise<any>; }
}

const REGION_NAMES = [
  'Tigray', 'Afar', 'Amhara', 'Benishangul-Gumuz', 'Oromia', 'Somali', 'Harari',
  'Gambela', 'Addis Ababa', 'Dire Dawa', 'Sidama', 'South West Ethiopia',
  'Central Ethiopia', 'South Ethiopia',
];
export const normalizeEthiopianRegionName = (name: string) => name.toLowerCase().replace(/[^a-z]/g, '');
const regionAliases: Record<string, string> = {
  snnp: 'South Ethiopia', snnpr: 'South Ethiopia',
  southernnationsnationalitiesandpeoples: 'South Ethiopia', southern: 'South Ethiopia',
  benishangulgumuz: 'Benishangul-Gumuz', benishangulgumz: 'Benishangul-Gumuz',
  swethiopia: 'South West Ethiopia',
};
export const resolveEthiopianRegionName = (name?: string) => {
  if (!name) return '';
  const key = normalizeEthiopianRegionName(name);
  return regionAliases[key] || REGION_NAMES.find((region) => normalizeEthiopianRegionName(region) === key) || name;
};

async function getGoogleMapsLibraries(): Promise<any> {
  const googleMaps = window.google?.maps;
  if (!googleMaps?.importLibrary) {
    throw new Error('Google Maps loaded without dynamic library support. Remove any other Google Maps script from the page and reload.');
  }
  const [mapsLibrary, markerLibrary, coreLibrary] = await Promise.all([
    googleMaps.importLibrary('maps'),
    googleMaps.importLibrary('marker'),
    googleMaps.importLibrary('core'),
  ]);
  return { ...mapsLibrary, ...markerLibrary, ...coreLibrary };
}

function loadGoogleMaps(apiKey: string): Promise<any> {
  if (window.google?.maps?.importLibrary) return getGoogleMapsLibraries();
  if (window.__ethiopiaGoogleMapsPromise) return window.__ethiopiaGoogleMapsPromise;

  window.__ethiopiaGoogleMapsPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&v=weekly`;
    script.async = true;
    script.defer = true;
    script.onload = () => window.google?.maps?.importLibrary
      ? resolve()
      : reject(new Error('Google Maps loaded without dynamic library support.'));
    script.onerror = () => reject(new Error('Google Maps could not load. Check network access, API key restrictions, and that Maps JavaScript API is enabled.'));
    document.head.appendChild(script);
  }).then(getGoogleMapsLibraries);
  return window.__ethiopiaGoogleMapsPromise;
}

export const EthiopiaDiseaseMap: React.FC<Props> = ({ cases }) => {
  const mapElement = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);
  const mapsLibraryRef = useRef<any>(null);
  const markers = useRef<any[]>([]);
  const infoWindow = useRef<any>(null);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim();

  const pointGroups = useMemo(() => {
    const groups = new Map<string, GeoDiagnosis[]>();
    cases.forEach((item) => {
      const lat = Number(item.latitude);
      const lng = Number(item.longitude);
      if (item.latitude == null || item.longitude == null || !Number.isFinite(lat) || !Number.isFinite(lng) || lat < 3 || lat > 15 || lng < 33 || lng > 48) return;
      const key = `${lat.toFixed(5)},${lng.toFixed(5)}`;
      groups.set(key, [...(groups.get(key) || []), item]);
    });
    return Array.from(groups.entries()).map(([key, items]) => {
      const [lat, lng] = key.split(',').map(Number);
      return { key, items, position: { lat, lng }, level: items.length >= 5 ? 'outbreak' : items.length >= 2 ? 'moderate' : 'low' };
    });
  }, [cases]);

  useEffect(() => {
    if (!apiKey) {
      setMapError(null);
      setMapReady(false);
      return;
    }
    let active = true;
    setMapError(null);
    void loadGoogleMaps(apiKey).then((maps) => {
      if (!active || !mapElement.current || mapInstance.current) return;
      mapsLibraryRef.current = maps;
      mapInstance.current = new maps.Map(mapElement.current, {
        center: { lat: 9.145, lng: 40.4897 },
        zoom: 5,
        minZoom: 4,
        maxZoom: 18,
        mapTypeId: 'roadmap',
        streetViewControl: false,
        mapTypeControl: true,
        fullscreenControl: true,
        clickableIcons: false,
      });
      infoWindow.current = new maps.InfoWindow();
      setMapReady(true);
    }).catch((error) => {
      if (active) setMapError(error?.message || 'Unable to initialize Google Maps.');
    });
    return () => { active = false; };
  }, [apiKey]);

  useEffect(() => {
    if (!mapReady || !mapInstance.current || !mapsLibraryRef.current) return;
    const maps = mapsLibraryRef.current;
    markers.current.forEach((marker) => marker.setMap(null));
    markers.current = pointGroups.map((group) => {
      const color = group.level === 'outbreak' ? '#dc2626' : group.level === 'moderate' ? '#eab308' : '#16a34a';
      const marker = new maps.Marker({
        map: mapInstance.current,
        position: group.position,
        title: `${group.items.length} diagnosis(es) - ${group.level} hotspot`,
        icon: {
          path: maps.SymbolPath.CIRCLE,
          fillColor: color,
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2,
          scale: Math.min(13, 7 + Math.log2(group.items.length)),
        },
        label: group.items.length > 1 ? { text: String(group.items.length), color: '#ffffff', fontSize: '10px', fontWeight: '700' } : undefined,
      });
      marker.addListener('click', () => {
        const content = document.createElement('div');
        content.className = 'p-1 text-sm';
        const heading = document.createElement('strong');
        heading.textContent = `${group.items.length} diagnosis(es) - ${group.level} hotspot`;
        content.appendChild(heading);
        group.items.slice(0, 6).forEach((item) => {
          const detail = document.createElement('div');
          detail.textContent = `${item.disease_class || 'Unknown disease'} - ${item.farmer_name || 'Farmer'}${item.region ? ` - ${item.region}` : ''}`;
          content.appendChild(detail);
        });
        if (group.items.length > 6) {
          const more = document.createElement('div');
          more.textContent = `And ${group.items.length - 6} more`;
          content.appendChild(more);
        }
        infoWindow.current.setContent(content);
        infoWindow.current.open({ map: mapInstance.current, anchor: marker });
      });
      return marker;
    });
  }, [mapReady, pointGroups]);

  return (
    <div className="space-y-2">
      <div ref={mapElement} className="h-[480px] w-full overflow-hidden rounded-xl border border-stone-200 bg-stone-100 dark:border-stone-800" role="application" aria-label="Google Map of Ethiopia with maize disease diagnosis hotspots" />
      {!apiKey && <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/40 dark:text-amber-200" role="status">Google Maps API key is not configured. Set <code>VITE_GOOGLE_MAPS_API_KEY</code> in the frontend .env file, enable Maps JavaScript API for that key, then restart Vite.</p>}
      {mapError && <p className="rounded-lg bg-red-50 p-3 text-xs text-red-800 dark:bg-red-950/40 dark:text-red-200" role="alert">{mapError}</p>}
      <p className="text-[11px] text-stone-500">Google Maps - Ethiopia. Hotspots group diagnoses at the same GPS point. Select a region above to filter regional records.</p>
    </div>
  );
};
