import axios from 'axios';
import { Platform } from 'react-native';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
