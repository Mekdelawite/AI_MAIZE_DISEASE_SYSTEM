import { apiRequest } from './api';
import { CropCalendarData, WeatherData } from '../types/api';

export const weatherService = {
  async getCurrentByCity(city: string, units: 'metric' | 'imperial' = 'metric'): Promise<WeatherData> {
    const res = await apiRequest<any>('/api/weather/current', {
      method: 'GET',
      params: { city: city.trim(), units },
    });
    return res?.weather || res;
  },

  async getFarmerWeather(units: 'metric' | 'imperial' = 'metric'): Promise<WeatherData> {
    const res = await apiRequest<any>('/api/weather/farmer', {
      method: 'GET',
      params: { units },
    });
    return res?.weather || res;
  },

  async getCropCalendar(): Promise<CropCalendarData> {
    const res = await apiRequest<any>('/api/crop-calendar', {
      method: 'GET',
    });
    return res?.crop_calendar || res;
  },
};
