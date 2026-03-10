import { useState, useEffect, useCallback } from 'react';
import { dishesApi } from '../../../shared/api';

export function useMenu(params = {}) {
  const [dishes, setDishes] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMenu = useCallback(async (queryParams = {}) => {
    setLoading(true);
    setError(null);
    const catRes = await dishesApi.getCategories();
    const varRes = await dishesApi.getVariants({ ...params, ...queryParams });
    if (!catRes.success) setError(catRes.message);
    else if (!varRes.success) setError(varRes.message);
    if (catRes.success) setCategories(catRes.categories || []);
    if (varRes.success) setDishes(varRes.dishes || []);
    setLoading(false);
  }, [params.category, params.calories_min, params.calories_max, params.price_min, params.price_max]);

  useEffect(() => {
    fetchMenu();
  }, [fetchMenu]);

  return { dishes, categories, loading, error, refetch: fetchMenu };
}
