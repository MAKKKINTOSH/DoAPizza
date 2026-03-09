// Мок-данные для пиццерии с размерами

export const PIZZA_SIZES = [
  { id: 'small', name: 'Маленькая', diameter: 25, multiplier: 0.7 },
  { id: 'medium', name: 'Средняя', diameter: 30, multiplier: 1 },
  { id: 'large', name: 'Большая', diameter: 35, multiplier: 1.3 },
];

export const MOCK_DISHES = [
  {
    id: 1,
    name: 'Маргарита',
    description: 'Томатный соус, моцарелла, свежий базилик',
    category: 'pizza',
    image: 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400',
    basePrice: 399,
    weight: 450,
    calories: 210,
    hasSizes: true,
    isPopular: true,
  },
  {
    id: 2,
    name: 'Пепперони',
    description: 'Острая салями, томатный соус, моцарелла',
    category: 'pizza',
    image: 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=400',
    basePrice: 449,
    weight: 520,
    calories: 280,
    hasSizes: true,
    isPopular: true,
  },
  {
    id: 3,
    name: 'Четыре сыра',
    description: 'Моцарелла, горгонзола, пармезан, дор блю',
    category: 'pizza',
    image: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400',
    basePrice: 499,
    weight: 480,
    calories: 320,
    hasSizes: true,
  },
  {
    id: 4,
    name: 'Гавайская',
    description: 'Курица, ананасы, моцарелла, томатный соус',
    category: 'pizza',
    image: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400',
    basePrice: 469,
    weight: 500,
    calories: 250,
    hasSizes: true,
  },
  {
    id: 5,
    name: 'Мясная',
    description: 'Бекон, ветчина, пепперони, курица, моцарелла',
    category: 'pizza',
    image: 'https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=400',
    basePrice: 549,
    weight: 580,
    calories: 350,
    hasSizes: true,
    isPopular: true,
  },
  {
    id: 6,
    name: 'Кола',
    description: 'Классическая газировка 0.5 л',
    category: 'drinks',
    image: 'https://images.unsplash.com/photo-1554866585-cd94860890b7?w=400',
    basePrice: 99,
    weight: 500,
    calories: 42,
    hasSizes: false,
  },
  {
    id: 7,
    name: 'Чизкейк',
    description: 'Классический нью-йоркский чизкейк',
    category: 'desserts',
    image: 'https://images.unsplash.com/photo-1533134242443-d4ea6f0b0576?w=400',
    basePrice: 199,
    weight: 150,
    calories: 350,
    hasSizes: false,
  },
];

export const CATEGORY_NAMES = {
  pizza: 'Пицца',
  drinks: 'Напитки',
  desserts: 'Десерты',
};

export const PROMO_BANNERS = [
  {
    id: 1,
    title: 'Две пиццы по цене одной',
    subtitle: 'При заказе от 800 ₽ — вторая пицца в подарок',
    accent: 'Акция',
  },
  {
    id: 2,
    title: 'Бесплатная доставка',
    subtitle: 'При заказе от 1 000 ₽',
    accent: 'Выгодно',
  },
];
