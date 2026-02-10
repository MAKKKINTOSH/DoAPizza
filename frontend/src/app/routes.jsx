import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '../widgets/AppLayout';
import { MenuPage } from '../pages/MenuPage/MenuPage';
import { AboutPage } from '../pages/AboutPage/AboutPage';
import { CheckoutPage } from '../pages/CheckoutPage/CheckoutPage';
import { LoginPage } from '../pages/LoginPage/LoginPage';
import { AdminPage } from '../pages/AdminPage/AdminPage';
import { ProfilePage } from '../pages/ProfilePage/ProfilePage';
import { CourierOrdersPage } from '../pages/CourierOrdersPage/CourierOrdersPage';
import { useAuth } from '../features/auth';

export function AppRoutes() {
  function RequireAuth({ children }) {
    const { isAuthenticated } = useAuth();

    if (!isAuthenticated) {
      return <Navigate to="/login" replace />;
    }

    return children;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<MenuPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/cart" element={<Navigate to="/" replace />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/profile"
            element={(
              <RequireAuth>
                <ProfilePage />
              </RequireAuth>
            )}
          />
          <Route path="/courier-orders" element={<RequireAuth><CourierOrdersPage /></RequireAuth>} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
