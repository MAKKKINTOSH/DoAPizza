import { AuthProvider } from '../features/auth';
import { CartProvider } from '../entities/cart';

export function Providers({ children }) {
  return (
    <AuthProvider>
      <CartProvider>{children}</CartProvider>
    </AuthProvider>
  );
}
