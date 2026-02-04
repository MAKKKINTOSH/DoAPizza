import { createContext, useContext, useReducer, useCallback } from 'react';
import { PIZZA_SIZES } from '../../dish/model/mockData';

const CartContext = createContext(null);

const initialState = {
  items: [],
  totalPrice: 0,
};

function getItemPrice(item) {
  if (item.sizeId && item.dish.hasSizes) {
    const size = PIZZA_SIZES.find((s) => s.id === item.sizeId);
    return size ? Math.round(item.dish.basePrice * size.multiplier) : item.dish.basePrice;
  }
  return item.dish.basePrice;
}

function recalcTotal(items) {
  return items.reduce((sum, item) => sum + getItemPrice(item) * item.quantity, 0);
}

function cartReducer(state, action) {
  switch (action.type) {
    case 'ADD': {
      const { dish, quantity = 1, sizeId } = action.payload;
      const existingIndex = state.items.findIndex(
        (i) => i.dish.id === dish.id && i.sizeId === (sizeId || null)
      );
      let newItems;
      if (existingIndex >= 0) {
        newItems = state.items.map((item, idx) =>
          idx === existingIndex ? { ...item, quantity: item.quantity + quantity } : item
        );
      } else {
        newItems = [...state.items, { dish, quantity, sizeId: dish.hasSizes ? sizeId : null }];
      }
      return { items: newItems, totalPrice: recalcTotal(newItems) };
    }
    case 'REMOVE': {
      const { dishId, sizeId } = action.payload;
      const newItems = state.items.filter(
        (i) => !(i.dish.id === dishId && i.sizeId === (sizeId || null))
      );
      return { items: newItems, totalPrice: recalcTotal(newItems) };
    }
    case 'UPDATE_QUANTITY': {
      const { dishId, sizeId, quantity } = action.payload;
      if (quantity <= 0) {
        const newItems = state.items.filter(
          (i) => !(i.dish.id === dishId && i.sizeId === (sizeId || null))
        );
        return { items: newItems, totalPrice: recalcTotal(newItems) };
      }
      const newItems = state.items.map((item) =>
        item.dish.id === dishId && item.sizeId === (sizeId || null)
          ? { ...item, quantity }
          : item
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
  const [state, dispatch] = useReducer(cartReducer, initialState);

  const addItem = useCallback((dish, quantity = 1, sizeId = null) => {
    dispatch({ type: 'ADD', payload: { dish, quantity, sizeId } });
  }, []);

  const removeItem = useCallback((dishId, sizeId = null) => {
    dispatch({ type: 'REMOVE', payload: { dishId, sizeId } });
  }, []);

  const updateQuantity = useCallback((dishId, sizeId, quantity) => {
    dispatch({ type: 'UPDATE_QUANTITY', payload: { dishId, sizeId, quantity } });
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
