import axios from 'axios';

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL,  // e.g. http://localhost:8000
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' }
});


// ─── Authorization check ────────────────────────────────────────

export function authorize() {
  return API.get('/api/authorize');
}

// ─── Authentication API ────────────────────────────────────────

// register(username, email, password)
export async function register(username, email, password) {
  return API.post('/api/register', { username, email, password });
}

// login(email, password)
export async function login(email, password) {
  const res = await API.post('/api/login', { email, password });
  localStorage.setItem('access_token', res.data.access_token);
  return res;
}

// logout()
export async function logout() {
  const res = await API.post('/api/logout');
  localStorage.removeItem('access_token');
  return res;
}

// getProfile()
export function getProfile() {
  return API.get('/api/profile');
}

// changePassword(oldPassword, newPassword)
export function changePassword(oldPassword, newPassword) {
  return API.post('/api/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  });
}
