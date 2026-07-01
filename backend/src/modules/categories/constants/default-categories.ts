import { CategoryType } from '../entities/category-type.enum';

export interface DefaultCategory {
  name: string;
  type: CategoryType;
  icon: string;
  color: string;
}

/**
 * Danh mục mặc định được tạo cho mỗi người dùng mới.
 * Mỗi danh mục có màu cố định để dùng nhất quán trên chip, biểu đồ, thanh ngân sách.
 */
export const DEFAULT_CATEGORIES: DefaultCategory[] = [
  { name: 'Lương', type: CategoryType.INCOME, icon: '💰', color: '#16A34A' },
  { name: 'Thưởng', type: CategoryType.INCOME, icon: '🎁', color: '#14B8A6' },
  { name: 'Đầu tư', type: CategoryType.INCOME, icon: '📈', color: '#06B6D4' },
  { name: 'Ăn uống', type: CategoryType.EXPENSE, icon: '🍜', color: '#F59E0B' },
  { name: 'Di chuyển', type: CategoryType.EXPENSE, icon: '🚗', color: '#6366F1' },
  { name: 'Hóa đơn', type: CategoryType.EXPENSE, icon: '🧾', color: '#EF4444' },
  { name: 'Mua sắm', type: CategoryType.EXPENSE, icon: '🛍️', color: '#EC4899' },
  { name: 'Giải trí', type: CategoryType.EXPENSE, icon: '🎬', color: '#8B5CF6' },
  { name: 'Sức khỏe', type: CategoryType.EXPENSE, icon: '💊', color: '#84CC16' },
];
