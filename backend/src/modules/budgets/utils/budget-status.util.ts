export type BudgetStatus = 'SAFE' | 'WARNING' | 'EXCEEDED';

/**
 * Quy tắc trạng thái ngân sách dựa trên % đã dùng:
 *  - EXCEEDED: > 100% (đã vượt hạn mức)
 *  - WARNING : 80% – 100% (sắp chạm hạn mức)
 *  - SAFE    : < 80%
 */
export function computeBudgetStatus(percentage: number): BudgetStatus {
  if (percentage > 100) return 'EXCEEDED';
  if (percentage >= 80) return 'WARNING';
  return 'SAFE';
}

/**
 * Tính % đã dùng (làm tròn). Trả 0 nếu hạn mức <= 0 để tránh chia cho 0.
 */
export function computeBudgetPercentage(spent: number, limit: number): number {
  if (limit <= 0) return 0;
  return Math.round((spent / limit) * 100);
}
