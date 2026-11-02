import { apiRequest } from './api';
import { CropCalendarData, FarmerWeatherForecastData, SoilWaterEstimate, WeatherData } from '../types/api';

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

  async getFarmerForecast(): Promise<FarmerWeatherForecastData> {
    return apiRequest<FarmerWeatherForecastData>('/api/weather/farmer/forecast', {
      method: 'GET',
    });
  },

  async getCropCalendar(): Promise<CropCalendarData> {
    return apiRequest<CropCalendarData>('/api/crop-calendar', {
      method: 'GET',
    });
  },

  async getSoilWaterEstimate(): Promise<SoilWaterEstimate> {
    return apiRequest<SoilWaterEstimate>('/api/crop-calendar/soil-water', { method: 'GET' });
  },
};
