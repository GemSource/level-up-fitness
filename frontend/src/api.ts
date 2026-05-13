import axios from 'axios';

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export const api = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 60000,
});

export const createProfile = (data: any) => api.post('/profile', data).then(r => r.data);
export const getProfile = (id: string) => api.get(`/profile/${id}`).then(r => r.data);
export const getDashboard = (id: string) => api.get(`/profile/${id}/dashboard`).then(r => r.data);
export const getWorkout = (id: string, wid: string) => api.get(`/profile/${id}/workout/${wid}`).then(r => r.data);
export const listWorkouts = (id: string) => api.get(`/profile/${id}/workouts`).then(r => r.data);
export const logWorkout = (id: string, payload: any) => api.post(`/profile/${id}/workout/log`, payload).then(r => r.data);
export const bossFight = (id: string, payload: any) => api.post(`/profile/${id}/boss-fight`, payload).then(r => r.data);
export const getAchievements = (id: string) => api.get(`/profile/${id}/achievements`).then(r => r.data);
export const getProgress = (id: string) => api.get(`/profile/${id}/progress`).then(r => r.data);
export const askCoach = (id: string, question?: string) => api.post(`/profile/${id}/ai-coach`, { question }).then(r => r.data);
export const getRankProgress = (id: string) => api.get(`/profile/${id}/rank-progress`).then(r => r.data);
export const getBossRequirements = (id: string) => api.get(`/profile/${id}/boss-fight/requirements`).then(r => r.data);
export const getShopCatalog = () => api.get('/shop/catalog').then(r => r.data);
export const getInventory = (id: string) => api.get(`/profile/${id}/inventory`).then(r => r.data);
export const buyItem = (id: string, item_key: string) => api.post(`/profile/${id}/shop/buy`, { item_key }).then(r => r.data);
export const activateItem = (id: string, item_key: string) => api.post(`/profile/${id}/inventory/activate`, { item_key }).then(r => r.data);
