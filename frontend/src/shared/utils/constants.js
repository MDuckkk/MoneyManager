export const CATEGORY_TYPE = { INCOME: 'INCOME', EXPENSE: 'EXPENSE' };

export const CATEGORY_TYPE_LABEL = {
  INCOME: 'Thu nhập',
  EXPENSE: 'Chi tiêu',
};

export const BUDGET_STATUS_LABEL = {
  SAFE: 'An toàn',
  WARNING: 'Sắp vượt',
  EXCEEDED: 'Đã vượt',
};

export const BUDGET_STATUS_CLASS = {
  SAFE: 'safe',
  WARNING: 'warning',
  EXCEEDED: 'exceeded',
};

/** Bảng màu dùng cho danh mục không gán màu / biểu đồ. */
export const CATEGORY_PALETTE = [
  '#6366F1', '#EC4899', '#14B8A6', '#F59E0B',
  '#8B5CF6', '#06B6D4', '#EF4444', '#84CC16',
  '#3B82F6', '#F97316',
];

export const colorFor = (color, index = 0) =>
  color || CATEGORY_PALETTE[index % CATEGORY_PALETTE.length];

/** Emoji icon mặc định khi danh mục chưa có icon. */
export const ICON_CHOICES = [
  '💰', '🎁', '📈', '🍜', '🚗', '🧾', '🛍️', '🎬',
  '💊', '🏠', '📚', '✈️', '☕', '🎮', '🐶', '💡',
];
