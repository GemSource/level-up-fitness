import axios from 'axios';
import { router } from 'expo-router';

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export const api = axios.create({
  baseURL: `${BASE}/api`,
  timeout: 60000,
});

// Global interceptor — redirect to paywall on 402
api.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 402) {
      router.replace('/paywall');
    }
    return Promise.reject(error);
  }
);

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
export const listExercises = (profileId?: string) => api.get('/exercises', { params: profileId ? { profile_id: profileId } : {} }).then(r => r.data);
export const createSideQuest = (id: string, payload: any) => api.post(`/profile/${id}/side-quest`, payload).then(r => r.data);
export const listSideQuests = (id: string) => api.get(`/profile/${id}/side-quests`).then(r => r.data);
export const logSideQuest = (id: string, payload: any) => api.post(`/profile/${id}/side-quest/log`, payload).then(r => r.data);
export const addCustomExercise = (id: string, payload: any) => api.post(`/profile/${id}/custom-exercise`, payload).then(r => r.data);
export const verifyPurchase = (id: string) => api.post(`/profile/${id}/verify-purchase`).then(r => r.data);
