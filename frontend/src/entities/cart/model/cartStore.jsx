import { createContext, useContext, useReducer, useCallback, useEffect } from 'react';

const CartContext = createContext(null);
const CART_STORAGE_KEY = 'doapizza_cart';

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) return { items: [], totalPrice: 0 };
    const data = JSON.parse(raw);
    const items = Array.isArray(data?.items) ? data.items : [];
    return { items, totalPrice: 0 };
  } catch {
    return { items: [], totalPrice: 0 };
  }
}

function saveToStorage(items) {
  try {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify({ items }));
  } catch {}
}

const initialState = {
  items: [],
  totalPrice: 0,
};

/**
 * Элемент корзины: { variant, quantity }
 * variant = { id, dish_name, dish_image, size, size_value, price, ... } — данные из API
 */
function getItemPrice(item) {
  const p = parseFloat(item.variant?.price);
  return Number.isFinite(p) ? p : 0;
}

function recalcTotal(items) {
  return items.reduce((sum, item) => sum + getItemPrice(item) * item.quantity, 0);
}

function cartReducer(state, action) {
  switch (action.type) {
    case 'ADD': {
      const { variant, quantity = 1 } = action.payload;
      const vid = variant?.id;
      if (!vid) return state;
      const existingIndex = state.items.findIndex((i) => i.variant.id === vid);
      let newItems;
      if (existingIndex >= 0) {
        newItems = state.items.map((item, idx) =>
          idx === existingIndex ? { ...item, quantity: item.quantity + quantity } : item
        );
      } else {
        newItems = [...state.items, { variant, quantity }];
      }
      return { items: newItems, totalPrice: recalcTotal(newItems) };
    }
    case 'REMOVE': {
      const { variantId } = action.payload;
      const newItems = state.items.filter((i) => i.variant.id !== variantId);
      return { items: newItems, totalPrice: recalcTotal(newItems) };
    }
    case 'UPDATE_QUANTITY': {
      const { variantId, quantity } = action.payload;
      if (quantity <= 0) {
        const newItems = state.items.filter((i) => i.variant.id !== variantId);
        return { items: newItems, totalPrice: recalcTotal(newItems) };
      }
      const newItems = state.items.map((item) =>
        item.variant.id === variantId ? { ...item, quantity } : item
      );
      return { items: newItems, totalPrice: recalcTotal(newItems) };
    }
    case 'CLEAR':
      return initialState;
    default:
      return state;
  }
}

export function CartProvider({ children }) {
  const [state, dispatch] = useReducer(cartReducer, loadFromStorage(), (init) => ({
    ...init,
    totalPrice: recalcTotal(init.items),
  }));

  useEffect(() => {
    saveToStorage(state.items);
  }, [state.items]);

  const addItem = useCallback((variant, quantity = 1) => {
    dispatch({ type: 'ADD', payload: { variant, quantity } });
  }, []);

  const removeItem = useCallback((variantId) => {
    dispatch({ type: 'REMOVE', payload: { variantId } });
  }, []);

  const updateQuantity = useCallback((variantId, quantity) => {
    dispatch({ type: 'UPDATE_QUANTITY', payload: { variantId, quantity } });
  }, []);

  const clearCart = useCallback(() => {
    dispatch({ type: 'CLEAR' });
  }, []);

  const getItemPriceFn = useCallback((item) => getItemPrice(item), []);

  return (
    <CartContext.Provider
      value={{
        items: state.items,
        totalPrice: state.totalPrice,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
        getItemPrice: getItemPriceFn,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within CartProvider');
  return ctx;
}
