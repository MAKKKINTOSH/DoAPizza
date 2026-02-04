import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '../widgets/AppLayout';
import { MenuPage } from '../pages/MenuPage/MenuPage';
import { AboutPage } from '../pages/AboutPage/AboutPage';
import { CheckoutPage } from '../pages/CheckoutPage/CheckoutPage';
import { LoginPage } from '../pages/LoginPage/LoginPage';
import { AdminPage } from '../pages/AdminPage/AdminPage';

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<MenuPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/cart" element={<Navigate to="/" replace />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
