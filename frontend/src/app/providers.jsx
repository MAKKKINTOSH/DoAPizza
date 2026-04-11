import { AuthProvider } from '../features/auth';
import { CartProvider } from '../entities/cart';
import { ToastProvider } from '../shared/ui/Toast';

export function Providers({ children }) {
  return (
    <AuthProvider>
      <CartProvider>
        <ToastProvider>{children}</ToastProvider>
      </CartProvider>
    </AuthProvider>
  );
}
